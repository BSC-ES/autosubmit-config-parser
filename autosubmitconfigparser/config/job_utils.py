# Copyright 2017-2020 Earth Sciences Department, BSC-CNS
#
# This file is part of Autosubmit.
#
# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import math

from bscearth.utils.date import date2str, chunk_end_date, chunk_start_date, subs_dates

from log.log import Log, AutosubmitCritical

CALENDAR_UNITSIZE_ENUM = {
    "hour": 0,
    "day": 1,
    "month": 2,
    "year": 3
}


def is_leap_year(year) -> bool:
    """Determine whether a year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def calendar_unitsize_isgreater(split_unit, chunk_unit) -> bool:
    """
    Check if the split unit is greater than the chunk unit
    :param split_unit:
    :param chunk_unit:
    :return: boolean
    """
    split_unit = split_unit.lower()
    chunk_unit = chunk_unit.lower()
    try:
        return CALENDAR_UNITSIZE_ENUM[split_unit] > CALENDAR_UNITSIZE_ENUM[chunk_unit]
    except KeyError:
        raise AutosubmitCritical(f"Invalid calendar unit size")


def calendar_unitsize_getlowersize(unitsize) -> str:
    """
    Get the lower size of a calendar unit
    :return: str
    """
    unit_size = unitsize.lower()
    unit_value = CALENDAR_UNITSIZE_ENUM[unit_size]
    if unit_value == 0:
        return "hour"
    else:
        return list(CALENDAR_UNITSIZE_ENUM.keys())[unit_value - 1]


def calendar_get_month_days(date_str) -> int:
    """
    Get the number of days in a month
    :param date_str: Date in string format (YYYYMMDD)
    :return: int
    """
    year = int(date_str[0:4])
    month = int(date_str[4:6])
    if month == 2:
        if is_leap_year(year):
            return 29
        else:
            return 28
    elif month in [4, 6, 9, 11]:
        return 30
    else:
        return 31


def get_chunksize_in_hours(date_str, chunk_unit, chunk_length) -> int:
    if is_leap_year(int(date_str[0:4])):
        num_days_in_a_year = 366
    else:
        num_days_in_a_year = 365
    if chunk_unit == "year":
        chunk_size_in_hours = num_days_in_a_year * 24 * chunk_length
    elif chunk_unit == "month":
        chunk_size_in_hours = calendar_get_month_days(date_str) * 24 * chunk_length
    elif chunk_unit == "day":
        chunk_size_in_hours = 24 * chunk_length
    else:
        chunk_size_in_hours = chunk_length
    return chunk_size_in_hours


def calendar_split_size_isvalid(date_str, split_size, split_unit,
                                chunk_size_in_hours) -> bool:
    """
    Check if the split size is valid for the calendar
    :param date_str: Date in string format (YYYYMMDD)
    :param split_size: Size of the split
    :param split_unit: Unit of the split
    :param chunk_size_in_hours: chunk size in hours
    :return: bool
    """
    if is_leap_year(int(date_str[0:4])):
        num_days_in_a_year = 366
    else:
        num_days_in_a_year = 365

    if split_unit == "year":
        split_size_in_hours = num_days_in_a_year * 24 * split_size
    elif split_unit == "month":
        split_size_in_hours = calendar_get_month_days(date_str) * 24 * split_size
    elif split_unit == "day":
        split_size_in_hours = 24 * split_size
    else:
        split_size_in_hours = split_size

    if split_size_in_hours != chunk_size_in_hours:
        Log.warning(
            f"After calculations, the total sizes are: SplitSize*SplitUnitSize:{split_size_in_hours} hours, ChunkSize*ChunkUnitsize:{chunk_size_in_hours} hours.")
    else:
        Log.debug(f"Split size in hours: {split_size_in_hours}, Chunk size in hours: {chunk_size_in_hours}")
    return split_size_in_hours <= chunk_size_in_hours


def calendar_chunk_section(exp_data, section, date, chunk) -> int:
    """
    Calendar for chunks
    :param section:
    :param parameters:
    :return: int
    """
    # next_auto_date = date
    splits = 0
    jobs_data = exp_data.get('JOBS', {})
    split_unit = str(exp_data.get("EXPERIMENT", {}).get('SPLITSIZEUNIT',
                                                        jobs_data.get(section, {}).get("SPLITSIZEUNIT", None))).lower()
    chunk_unit = str(exp_data.get("EXPERIMENT", {}).get('CHUNKSIZEUNIT', "day")).lower()
    split_policy = str(exp_data.get("EXPERIMENT", {}).get('SPLITPOLICY', jobs_data.get(section, {}).get("SPLITPOLICY",
                                                                                                        "flexible"))).lower()
    if chunk_unit == "hour":
        raise AutosubmitCritical(
            "Chunk unit is hour, Autosubmit doesn't support lower than hour splits. Please change the chunk unit to day or higher. Or don't use calendar splits.")
    if jobs_data.get(section, {}).get("RUNNING", "once") != "once":
        chunk_length = int(exp_data.get("EXPERIMENT", {}).get('CHUNKSIZE', 1))
        cal = str(exp_data.get('CALENDAR', "standard")).lower()
        chunk_start = chunk_start_date(
            date, chunk, chunk_length, chunk_unit, cal)
        chunk_end = chunk_end_date(
            chunk_start, chunk_length, chunk_unit, cal)
        run_days = subs_dates(chunk_start, chunk_end, cal)
        if split_unit == "none":
            split_unit = calendar_unitsize_getlowersize(chunk_unit)
        if calendar_unitsize_isgreater(split_unit, chunk_unit):
            raise AutosubmitCritical(
                "Split unit is greater than chunk unit. Autosubmit doesn't support this configuration. Please change the split unit to day or lower. Or don't use calendar splits.")
        if split_unit == "hour":
            num_max_splits = run_days * 24
        elif split_unit == "month":
            num_max_splits = run_days / 12
        elif split_unit == "year":
            if not is_leap_year(chunk_start.year) or cal == "noleap":
                num_max_splits = run_days / 365
            else:
                num_max_splits = run_days / 366
        else:
            num_max_splits = run_days
        split_size = get_split_size(exp_data, section)
        chunk_size_in_hours = get_chunksize_in_hours(date2str(chunk_start), chunk_unit, chunk_length)
        if not calendar_split_size_isvalid(date2str(chunk_start), split_size, split_unit, chunk_size_in_hours):
            raise AutosubmitCritical(
                f"Invalid split size for the calendar. The split size is {split_size} and the unit is {split_unit}.")
        splits = num_max_splits / split_size
        if not splits.is_integer() and split_policy == "flexible":
            Log.warning(
                f"The number of splits:{num_max_splits}/{split_size} is not an integer. The number of splits will be rounded up due the flexible split policy.\n You can modify the SPLITPOLICY parameter in the section {section} to 'strict' to avoid this behavior.")
        elif not splits.is_integer() and split_policy == "strict":
            raise AutosubmitCritical(
                f"The number of splits is not an integer. Autosubmit can't continue.\nYou can modify the SPLITPOLICY parameter in the section {section} to 'flexible' to roundup the number. Or change the SPLITSIZE parameter to a value in which the division is an integer.")
        splits = math.ceil(splits)
        Log.info(f"For the section {section} with date:{date2str(chunk_start)} the number of splits is {splits}.")
    return splits


def get_split_size_unit(data, section) -> str:
    split_unit = str(data.get('JOBS', {}).get(section, {}).get('SPLITSIZEUNIT', "none")).lower()
    if split_unit == "none":
        split_unit = str(data.get('EXPERIMENT', {}).get("CHUNKSIZEUNIT", "day")).lower()
        if split_unit == "year":
            return "month"
        elif split_unit == "month":
            return "day"
        elif split_unit == "day":
            return "hour"
        else:
            return "day"
    return split_unit


def get_split_size(as_conf, section) -> int:
    job_data = as_conf.get('JOBS', {}).get(section, {})
    return int(job_data.get("SPLITSIZE", 1))
