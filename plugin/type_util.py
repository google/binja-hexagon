#
# Copyright (C) 2020 Google LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import collections
import inspect
import sys
import types
import typing


def type_check(func):
  '''A decorator for simple type checks at run-time.
     So far this only works for simple types, Any, Tuple, Union and Optional.
     The return type can be a simple generator.
  '''
  if skip_type_check:
    return func
  type_hints = typing.get_type_hints(func)
  func_args = inspect.getfullargspec(func)[0]

  def has_any_type(val, type_list):
    return any(has_type(val, t) for t in type_list)

  def has_type(val, type_hint):
    if type_hint == typing.Any:
      return True
    if isinstance(type_hint, typing._GenericAlias):
      orig = type_hint.__origin__
      if orig == typing.Union:
        return has_any_type(val, type_hint.__args__)
      if orig == list:
        if not isinstance(val, list):
          return False
        return all(has_any_type(x, type_hint.__args__) for x in val)
      if orig == tuple:
        if not isinstance(val, tuple):
          return False
        if len(val) != len(type_hint.__args__):
          return False
        return all(has_type(v, t) for v, t in zip(val, type_hint.__args__))
    if isinstance(type_hint, type):
      return isinstance(val, type_hint)
    else:
      # Python 3.9 adds type hints such as list[int].
      # These will be of type typing.GenericAlias
      raise TypeError("unknown type:", type_hint)

  def check_type(name, val):
    if name in type_hints:
      type_hint = type_hints[name]
      if not has_type(val, type_hint):
        raise TypeError("%s is of type %s expected: %s\nval:%s" %
                        (name, type(val), type_hint, repr(val)))

  def check_generator(name, val):
    '''Gets a generator and returns a type checked generator'''
    if name not in type_hints:
      yield from val
    else:
      type_hint = type_hints[name]
      if (isinstance(type_hint, typing._GenericAlias) and
          type_hint.__origin__ == collections.abc.Generator):
        res_type = type_hint.__args__[0]
        # SendType and ReturnType are not implemented
        assert type_hint.__args__[1] is type(None)
        assert type_hint.__args__[2] is type(None)
        for y in val:
          if has_type(y, res_type):
            yield y
          else:
            raise TypeError(
                "iterator element is of type %s expected: %s\nval:%s" %
                (type(y), res_type, repr(y)))
      else:
        raise TypeError("%s is of type %s expected: %s\nval:%s" %
                        (name, type(val), type_hint, repr(val)))

  def wrapper(*args, **kwargs):
    for i, val in enumerate(args):
      check_type(func_args[i], val)
    for n, val in kwargs.items():
      check_type(n, val)
    res = func(*args, **kwargs)
    # Allowing generators as return type
    if isinstance(res, types.GeneratorType):
      return check_generator('return', res)
    else:
      check_type('return', res)
      return res

  if func.__doc__:
    wrapper.__doc__ = func.__doc__
  return wrapper


skip_type_check = False
if sys.version_info.minor < 7:
  skip_type_check = True
