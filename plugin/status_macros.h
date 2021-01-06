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

#include "absl/base/optimization.h"
#include "absl/status/status.h"

// Internal helper for concatenating macro values.
#define MACROS_IMPL_CONCAT_INNER_(x, y) x##y
#define MACROS_IMPL_CONCAT(x, y) MACROS_IMPL_CONCAT_INNER_(x, y)

#define RETURN_IF_ERROR(expr)                                                  \
  do {                                                                         \
    const auto status = (expr);                                                \
    if (ABSL_PREDICT_FALSE(!status.ok())) {                                    \
      return status;                                                           \
    }                                                                          \
  } while (0);

#define ASSIGN_OR_RETURN(lhs, rexpr)                                           \
  ASSIGN_OR_RETURN_IMPL(MACROS_IMPL_CONCAT(_statusor, __LINE__), lhs, rexpr)

#define ASSIGN_OR_RETURN_IMPL(statusor, lhs, rexpr)                            \
  auto statusor = (rexpr);                                                     \
  if (ABSL_PREDICT_FALSE(!statusor.ok())) {                                    \
    return statusor.status();                                                  \
  }                                                                            \
  lhs = std::move(statusor).value();
