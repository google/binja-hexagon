// Copyright (C) 2020 Google LLC
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#pragma once

#include <type_traits>

#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/types/optional.h"
#include "plugin/status_macros.h"
#include "gmock/gmock.h"

#define ASSERT_OK_AND_ASSIGN(lhs, rexpr)                                       \
  ASSERT_OK_AND_ASSIGN_IMPL(MACROS_IMPL_CONCAT(_statusor, __LINE__), lhs, rexpr)

#define ASSERT_OK_AND_ASSIGN_IMPL(statusor, lhs, rexpr)                        \
  auto statusor = (rexpr);                                                     \
  ASSERT_THAT(statusor.status(), absl::IsOk());                                \
  lhs = std::move(statusor).value();

namespace absl {
namespace internal {

class IsOkMatcher {
public:
  template <typename StatusT>
  bool MatchAndExplain(const StatusT &status_container,
                       ::testing::MatchResultListener *listener) const {
    if (!status_container.ok()) {
      *listener << "which is not OK";
      return false;
    }
    return true;
  }

  void DescribeTo(std::ostream *os) const { *os << "is OK"; }

  void DescribeNegationTo(std::ostream *os) const { *os << "is not OK"; }
};

class StatusIsMatcher {
public:
  StatusIsMatcher(const StatusIsMatcher &) = default;

  StatusIsMatcher(absl::StatusCode code,
                  absl::optional<absl::string_view> message)
      : code_(code), message_(message) {}

  template <typename T>
  bool MatchAndExplain(const T &value,
                       ::testing::MatchResultListener *listener) const {
    auto status = GetStatus(value);
    if (code_ != status.code()) {
      *listener << "whose error code is "
                << absl::StatusCodeToString(status.code());
      return false;
    }
    if (message_.has_value() && status.message() != message_.value()) {
      *listener << "whose error message is '" << message_.value() << "'";
      return false;
    }
    return true;
  }

  void DescribeTo(std::ostream *os) const {
    *os << "has a status code that is " << absl::StatusCodeToString(code_);
    if (message_.has_value()) {
      *os << ", and has an error message that is '" << message_.value() << "'";
    }
  }

  void DescribeNegationTo(std::ostream *os) const {
    *os << "has a status code that is not " << absl::StatusCodeToString(code_);
    if (message_.has_value()) {
      *os << ", and has an error message that is not '" << message_.value()
          << "'";
    }
  }

private:
  template <typename StatusT,
            typename std::enable_if<
                !std::is_void<decltype(std::declval<StatusT>().code())>::value,
                int>::type = 0>
  static const StatusT &GetStatus(const StatusT &status) {
    return status;
  }

  template <typename StatusOrT,
            typename StatusT = decltype(std::declval<StatusOrT>().status())>
  static StatusT GetStatus(const StatusOrT &status_or) {
    return status_or.status();
  }

  const absl::StatusCode code_;
  const absl::optional<std::string> message_;
};

} // namespace internal

inline ::testing::PolymorphicMatcher<internal::IsOkMatcher> IsOk() {
  return ::testing::MakePolymorphicMatcher(internal::IsOkMatcher{});
}

inline ::testing::PolymorphicMatcher<internal::StatusIsMatcher>
StatusIs(absl::StatusCode code,
         absl::optional<absl::string_view> message = absl::nullopt) {
  return ::testing::MakePolymorphicMatcher(
      internal::StatusIsMatcher(code, message));
}

} // namespace absl
