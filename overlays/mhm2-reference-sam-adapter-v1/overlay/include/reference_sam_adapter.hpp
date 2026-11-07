#ifndef ACCELERATE_MHM2_REFERENCE_SAM_ADAPTER_V1_HPP
#define ACCELERATE_MHM2_REFERENCE_SAM_ADAPTER_V1_HPP
#include <string>
#include <vector>
#include <utility>
#include <stdexcept>
#include <limits>
namespace reference_sam_adapter_v1 {
// SSW query is the contig slice; SAM query is the oriented read.
inline std::string from_contig_query(const std::string &cigar,
                                    int contig_begin, int contig_end, int contig_length,
                                    int read_begin, int read_end, int read_length) {
  if (contig_begin < 0 || contig_end < contig_begin || contig_end >= contig_length ||
      read_begin < 0 || read_end < read_begin || read_end >= read_length)
    throw std::invalid_argument("Invalid SSW coordinate bounds");
  std::vector<std::pair<int, char>> ops;
  long long n = 0;
  bool digits = false;
  for (char c : cigar) {
    if (c >= '0' && c <= '9') {
      n = n * 10 + (c - '0');
      if (n > std::numeric_limits<int>::max()) throw std::invalid_argument("CIGAR count overflow");
      digits = true;
    } else {
      if (!digits || n == 0 || std::string("M=XIDS").find(c) == std::string::npos)
        throw std::invalid_argument("Unsupported SSW CIGAR");
      ops.emplace_back(static_cast<int>(n), c); n = 0; digits = false;
    }
  }
  if (digits || ops.empty()) throw std::invalid_argument("Incomplete SSW CIGAR");
  int prefix = 0, suffix = 0;
  if (ops.front().second == 'S') { prefix = ops.front().first; ops.erase(ops.begin()); }
  if (!ops.empty() && ops.back().second == 'S') { suffix = ops.back().first; ops.pop_back(); }
  if (ops.empty() || prefix != contig_begin || suffix != contig_length - contig_end - 1)
    throw std::invalid_argument("SSW contig clipping mismatch");
  long long contig_used = 0, read_used = 0;
  std::string result;
  if (read_begin) result += std::to_string(read_begin) + "S";
  for (const auto &op : ops) {
    const char c = op.second;
    if (c == 'S') throw std::invalid_argument("Internal SSW soft clip");
    if (c == 'M' || c == '=' || c == 'X') { contig_used += op.first; read_used += op.first; }
    else if (c == 'I') contig_used += op.first;
    else if (c == 'D') read_used += op.first;
    result += std::to_string(op.first) + (c == 'I' ? "D" : c == 'D' ? "I" : std::string(1, c));
  }
  if (contig_used != contig_end - contig_begin + 1 || read_used != read_end - read_begin + 1)
    throw std::invalid_argument("SSW alignment consumption mismatch");
  if (read_end + 1 < read_length) result += std::to_string(read_length - read_end - 1) + "S";
  return result;
}
}
#endif
