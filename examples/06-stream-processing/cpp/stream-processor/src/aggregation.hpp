// aggregation.hpp — the pure part of the stream processor: order-event parsing, exact
// decimal money, and tumbling-window aggregation with no grace period. No Kafka in here, so
// ctest can exercise all of it.
//
// Money is a fixed-point integer (128-bit mantissa plus a decimal scale), never a double:
// a window total is the exact sum of the order totals and is rounded once, HALF_UP (half
// away from zero), when it is printed with two decimals.

#pragma once

#include <cstdint>
#include <map>
#include <optional>
#include <string>

#include <nlohmann/json.hpp>

namespace cndp {

using i128 = __int128;

inline i128 pow10_i128(int n) {
    i128 r = 1;
    for (int i = 0; i < n; ++i) r *= 10;
    return r;
}

inline std::string i128_to_string(i128 v) {
    if (v == 0) return "0";
    bool neg = v < 0;
    unsigned __int128 u = neg ? -static_cast<unsigned __int128>(v) : static_cast<unsigned __int128>(v);
    std::string s;
    while (u != 0) {
        s.insert(s.begin(), static_cast<char>('0' + static_cast<int>(u % 10)));
        u /= 10;
    }
    return neg ? "-" + s : s;
}

// value = mantissa / 10^scale
struct Decimal {
    i128 mantissa = 0;
    int scale = 0;
};

// A parsed mantissa has at most 36 digits (< 10^36) and a scale of at most 36. add() keeps
// every sum, aligned and also scaled to cents, below 10^37, so money()'s x100 and the
// rounding arithmetic stay inside 128 bits (about 1.7e38). Anything larger is rejected.
inline constexpr int kMaxDigits = 36;

// Parses a plain decimal number: [sign] digits [. digits] [e|E [sign] digits], exponent within
// +-30. Anything else (NaN, Infinity, hex, booleans, empty, too long) is rejected so one bad
// record cannot stall the stream.
inline std::optional<Decimal> parse_decimal(const std::string& text) {
    size_t i = 0, n = text.size();
    while (i < n && (text[i] == ' ' || text[i] == '\t')) ++i;
    while (n > i && (text[n - 1] == ' ' || text[n - 1] == '\t')) --n;
    if (i >= n || n - i > 64) return std::nullopt;

    bool neg = false;
    if (text[i] == '+' || text[i] == '-') neg = text[i++] == '-';

    std::string digits;
    int frac_digits = 0;
    bool seen_dot = false, any_digit = false;
    for (; i < n; ++i) {
        char c = text[i];
        if (c >= '0' && c <= '9') {
            digits.push_back(c);
            any_digit = true;
            if (seen_dot) ++frac_digits;
        } else if (c == '.' && !seen_dot) {
            seen_dot = true;
        } else {
            break;
        }
    }
    if (!any_digit) return std::nullopt;

    int exp = 0;
    if (i < n) {
        if (text[i] != 'e' && text[i] != 'E') return std::nullopt;
        ++i;
        bool eneg = false;
        if (i < n && (text[i] == '+' || text[i] == '-')) eneg = text[i++] == '-';
        if (i >= n) return std::nullopt;
        for (; i < n; ++i) {
            if (text[i] < '0' || text[i] > '9') return std::nullopt;
            exp = exp * 10 + (text[i] - '0');
            if (exp > 30) return std::nullopt;
        }
        if (eneg) exp = -exp;
    }

    size_t first = digits.find_first_not_of('0');
    digits = first == std::string::npos ? "0" : digits.substr(first);
    int scale = frac_digits - exp;
    int total_digits = static_cast<int>(digits.size()) + (scale < 0 ? -scale : 0);
    if (total_digits > kMaxDigits || scale > kMaxDigits) return std::nullopt;

    i128 m = 0;
    for (char c : digits) m = m * 10 + (c - '0');
    if (scale < 0) {
        m *= pow10_i128(-scale);
        scale = 0;
    }
    return Decimal{neg ? -m : m, scale};
}

// m * 10^by, or false when it would not fit in 128 bits (checked before the value is used).
inline bool scale_up(i128 m, int by, i128& out) {
    return !__builtin_mul_overflow(m, pow10_i128(by), &out);
}

// a + b, or nullopt when the aligned sum, or that sum in cents, would not stay below 10^37.
inline std::optional<Decimal> add(const Decimal& a, const Decimal& b) {
    int scale = a.scale > b.scale ? a.scale : b.scale;
    i128 am, bm, sum;
    if (!scale_up(a.mantissa, scale - a.scale, am) || !scale_up(b.mantissa, scale - b.scale, bm) ||
        __builtin_add_overflow(am, bm, &sum))
        return std::nullopt;
    const i128 limit = pow10_i128(kMaxDigits + 1);
    if (sum >= limit || sum <= -limit) return std::nullopt;
    if (scale < 2) {  // money() multiplies by 10^(2-scale)
        i128 cents;
        if (!scale_up(sum, 2 - scale, cents) || cents >= limit || cents <= -limit) return std::nullopt;
    }
    return Decimal{sum, scale};
}

// Two decimals, HALF_UP (halves round away from zero), e.g. 2.675 -> "2.68", -2.675 -> "-2.68".
inline std::string money(const Decimal& d) {
    bool neg = d.mantissa < 0;
    i128 abs = neg ? -d.mantissa : d.mantissa;
    i128 cents;
    if (d.scale <= 2) {
        cents = abs * pow10_i128(2 - d.scale);
    } else {
        i128 div = pow10_i128(d.scale - 2);
        cents = abs / div;
        if ((abs % div) * 2 >= div) ++cents;
    }
    i128 whole = cents / 100;
    int frac = static_cast<int>(cents % 100);
    std::string out = (neg && cents != 0) ? "-" : "";
    out += i128_to_string(whole);
    out += '.';
    if (frac < 10) out += '0';
    out += std::to_string(frac);
    return out;
}

// ---------------------------------------------------------------------------------------
// Order event parsing. merchant_id follows the Kafka Streams / Go versions: a string is used
// as is, a number or boolean becomes its JSON text, a missing / null / empty / object / array
// value drops the record. A missing or null total counts as 0; a total that is not a plain
// decimal is reported to the caller, which logs a WARN and skips the record.
// ---------------------------------------------------------------------------------------

struct OrderEvent {
    std::string merchant;
    std::string total_text;  // raw JSON text of the total ("10.00", "\"x\"", "true", ...)
};

namespace detail {
// SAX handler: remembers the raw text of the top-level merchant_id and total members.
struct EventSax {
    struct Slot {
        bool present = false, null = false, complex = false;
        std::string text;
    };
    Slot merchant, total;
    int depth = 0;
    Slot* current = nullptr;
    bool top_level_object = false;

    void put(const std::string& txt, bool is_null = false) {
        if (current && depth == 1) {
            current->present = true;
            current->null = is_null;
            current->text = txt;
        }
        current = nullptr;
    }
    void put_complex() {
        if (current && depth == 1) {
            current->present = true;
            current->complex = true;
        }
        current = nullptr;
    }
    bool null() { put("null", true); return true; }
    bool boolean(bool v) { put(v ? "true" : "false"); return true; }
    bool number_integer(nlohmann::json::number_integer_t v) { put(std::to_string(v)); return true; }
    bool number_unsigned(nlohmann::json::number_unsigned_t v) { put(std::to_string(v)); return true; }
    bool number_float(nlohmann::json::number_float_t, const std::string& s) { put(s); return true; }
    bool string(std::string& s) { put(s); return true; }
    bool binary(nlohmann::json::binary_t&) { return true; }
    bool start_object(std::size_t) {
        if (depth == 0) top_level_object = true;
        else put_complex();
        ++depth;
        return true;
    }
    bool end_object() { --depth; return true; }
    bool start_array(std::size_t) { put_complex(); ++depth; return true; }
    bool end_array() { --depth; return true; }
    bool key(std::string& k) {
        current = nullptr;
        if (depth == 1) current = k == "merchant_id" ? &merchant : k == "total" ? &total : nullptr;
        return true;
    }
    bool parse_error(std::size_t, const std::string&, const nlohmann::json::exception&) { return false; }
};
}  // namespace detail

// total_text is kept verbatim for the WARN line; strings are quoted only when the raw JSON
// was not a plain number.
inline std::optional<OrderEvent> parse_order_event(const std::string& raw) {
    // The old producer could leave leading bytes before the object; start at the first '{'.
    size_t start = raw.find('{');
    if (start == std::string::npos) return std::nullopt;
    detail::EventSax h;
    if (!nlohmann::json::sax_parse(raw.substr(start), &h) || !h.top_level_object) return std::nullopt;
    if (!h.merchant.present || h.merchant.null || h.merchant.complex || h.merchant.text.empty())
        return std::nullopt;
    OrderEvent ev;
    ev.merchant = h.merchant.text;
    if (!h.total.present || h.total.null) ev.total_text = "0";
    else if (h.total.complex) ev.total_text = "[object]";
    else ev.total_text = h.total.text;
    return ev;
}

// ---------------------------------------------------------------------------------------
// Tumbling windows, no grace (Kafka Streams TimeWindows.ofSizeWithNoGrace).
// ---------------------------------------------------------------------------------------

// Start of the window (epoch seconds) that contains a record time in epoch milliseconds.
inline int64_t window_start(int64_t ts_millis, int64_t window_seconds) {
    return (ts_millis / 1000 / window_seconds) * window_seconds;
}

struct WindowUpdate {
    int64_t start = 0;  // epoch seconds
    int64_t end = 0;
    int count = 0;
    Decimal total;
};

// Per-merchant window state: open windows plus the merchant's stream time (max record time
// seen). A record whose window already ended relative to stream time is late and dropped.
class MerchantWindows {
public:
    explicit MerchantWindows(int64_t window_seconds) : window_seconds_(window_seconds) {}

    // nullopt = dropped: late, or the sum would leave the supported range (overflowed()).
    std::optional<WindowUpdate> apply(int64_t ts_millis, const Decimal& amount) {
        overflowed_ = false;
        int64_t start = window_start(ts_millis, window_seconds_);
        if (ts_millis > stream_time_) stream_time_ = ts_millis;
        if ((start + window_seconds_) * 1000 <= stream_time_) return std::nullopt;  // late
        for (auto it = windows_.begin(); it != windows_.end();) {
            if ((it->first + window_seconds_) * 1000 <= stream_time_) it = windows_.erase(it);
            else ++it;
        }
        Acc& acc = windows_[start];
        auto sum = add(acc.total, amount);
        if (!sum) {  // out of the supported range: skip the record, keep the old total
            overflowed_ = true;
            return std::nullopt;
        }
        acc.total = *sum;
        ++acc.count;
        return WindowUpdate{start, start + window_seconds_, acc.count, acc.total};
    }

    size_t open_windows() const { return windows_.size(); }
    bool overflowed() const { return overflowed_; }  // the last apply() was refused for range

private:
    struct Acc {
        int count = 0;
        Decimal total;
    };
    int64_t window_seconds_;
    int64_t stream_time_ = 0;
    bool overflowed_ = false;
    std::map<int64_t, Acc> windows_;
};

// The JSON body of a revenue.by-merchant record. Revenue is spliced in as a JSON number with
// exactly two decimals.
inline std::string revenue_json(const std::string& merchant, const WindowUpdate& u) {
    return std::string("{\"window_start\":") + std::to_string(u.start) +
           ",\"window_end\":" + std::to_string(u.end) +
           ",\"merchant_id\":" + nlohmann::json(merchant).dump() +
           ",\"order_count\":" + std::to_string(u.count) +
           ",\"revenue\":" + money(u.total) + "}";
}

}  // namespace cndp
