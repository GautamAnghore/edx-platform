"""Simple utility functions that operate on course metadata.

Ths is a place to put simple functions that operate on course metadata. It
allows us to share code between the CourseDescriptor and CourseOverview
classes, which both need these type of functions.
"""
from datetime import datetime
from base64 import b32encode

from django.utils.timezone import UTC

from .fields import Date

DEFAULT_START_DATE = datetime(2030, 1, 1, tzinfo=UTC())


def clean_course_key(course_key, padding_char):
    """
    Encode a course's key into a unique, deterministic base32-encoded ID for the course.

    Arguments:
        course_key (CourseKejjy): A course key.
        padding_char (str): Character used for padding at end of the encoded string.
                            The standard value for this is '='.
    """
    return "course_{}".format(
        b32encode(unicode(course_key)).replace('=', padding_char)
    )


def get_url_from_course_location(location):
    """
    Given a course's location, returns the course's URL.

    Arguments:
        location (UsageKey): The location of said question.
    """
    return location.name


def get_course_display_name_with_default(course):
    """
    Calculates the display name for a course.

    Default to the display_name if it isn't None, else fall back to creating
    a name based on the URL.

    Unlike the rest of this module's functions, this function takes an entire course
    descriptor/overview as a parameter. While testing, it seems that there are times
    when course.display_name is not None, but course.location is None, which causes
    calling course.url_name to fail with an AttributeError. So, although we'd like to
    just pass in course.location and course.url_name as arguments to this function, we can't
    do so without breaking some tests.

    Arguments:
        course (CourseDescriptor|CourseOverview): descriptor or overview of said course.
    """
    return (
        course.display_name if course.display_name is not None else course.url_name.replace('_', ' ')
    ).replace('<', '&lt;').replace('>', '&gt;')


def get_number_from_course_location(location):
    """
    Given a course location, returns the course's number.

    Arguments:
        location (UsageKey): The location of the course in question.
    """
    return location.course


def has_course_started(start_date):
    """
    Given a course's start datetime, returns whether the current time is past it.

    Arguments:
        start_date (datetime): The start datetime of the course in question.
    """
    return datetime.now(UTC()) > start_date


def has_course_ended(end_date):
    """
    Given a course's end datetime, returns whether (a) it is not None (b) the current time is past it.

    Arguments:
        end_date (datetime): The end datetime of the course in question.
    """
    return datetime.now(UTC()) > end_date if end_date is not None else False


def _add_timezone_string(date_time):
    """
    Adds 'UTC' string to the end of start/end date and time texts.
    """
    return date_time + u" UTC"


def is_course_start_date_still_default(start, advertised_start):
    """
    Returns whether a course's start date hasn't yet been set.

    Arguments:
        start (datetime): The start datetime of the course in question.
        advertised_start (str): The advertised start date of the course in question.
    """
    return advertised_start is None and start == DEFAULT_START_DATE


def get_course_start_datetime_text(start, advertised_start, format_string, ugettext, strftime):
    """
    Calculates text to be shown to user regarding a course's start datetime in UTC..
    Prefers .advertised_start, then falls back to .start.

    Arguments:
        start (datetime): the start date of a course
        advertised_start (str): the advertised start date of a course, as a string
        format_string (str): the date format type, as passed to strftime
        ugettext (str -> str): a text localization function
        strftime (datetime, str -> str): a localized string formatting function
    """
    _ = ugettext

    def try_parse_iso_8601(text):
        try:
            result = Date().from_json(text)
            if result is None:
                result = text.title()
            else:
                result = strftime(result, format_string)
                if format_string == "DATE_TIME":
                    result = _add_timezone_string(result)
        except ValueError:
            result = text.title()

        return result

    if isinstance(advertised_start, basestring):
        return try_parse_iso_8601(advertised_start)
    elif is_course_start_date_still_default(start, advertised_start):
        # Translators: TBD stands for 'To Be Determined' and is used when a course
        # does not yet have an announced start date.
        return _('TBD')
    else:
        when = advertised_start or start
        if format_string == "DATE_TIME":
            return _add_timezone_string(strftime(when, format_string))
        return strftime(when, format_string)


def get_course_end_datetime_text(end, format_string, strftime_localized):
    """
    Returns a formatted string for a course's end date or datetime.
    If end is none, an empty string will be returned.

    Arguments:
        end (datetime): the end date of a course
        format_string (str): the date format type, as passed to strftime
        strftime_localized (datetime, str -> str): a localized string formatting function
    """
    if end is None:
        return ''
    else:
        formatted_date = strftime_localized(end, format_string)
        return formatted_date if format_string == "SHORT_DATE" else _add_timezone_string(formatted_date)


def may_certify_for_course(certificates_display_behavior, certificates_show_before_end, has_ended):
    """
    Returns whether it is acceptable to show the student a certificate download link for a course.

    Arguments:
        certificates_display_behavior (str): string describing the course's
            certificate display behavior.
            See CourseFields.certificates_display_behavior.help for more detail.
        certificates_show_before_end (bool): whether user can download the course's
            certificates before the course has ended.
        has_ended (bool): Whether the course has ended.
    """
    show_early = (
        certificates_display_behavior in ('early_with_info', 'early_no_info')
        or certificates_show_before_end
    )
    return show_early or has_ended
