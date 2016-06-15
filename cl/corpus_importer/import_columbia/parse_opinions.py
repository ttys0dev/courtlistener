# -*- coding: utf-8 -*-

# Functions to parse court data in XML format into a list of dictionaries.
import hashlib
import os
import re
import xml.etree.cElementTree as ET

import dateutil.parser as dparser
from juriscraper.lib.string_utils import titlecase, harmonize, clean_string, CaseNameTweaker

from cl.corpus_importer.court_regexes import state_pairs
from parse_judges import find_judge_names
from regexes_columbia import SPECIAL_REGEXES, FOLDER_DICT

# initialized once since it takes resources
CASE_NAME_TWEAKER = CaseNameTweaker()

# tags for which content will be condensed into plain text
SIMPLE_TAGS = [
    "reporter_caption", "citation", "caption", "court", "docket", "posture"
    ,"date", "hearing_date"
    ,"panel", "attorneys"
]

# regex that will be applied when condensing SIMPLE_TAGS content
STRIP_REGEX = [r'</?citation.*>', r'</?page_number.*>']

# types of opinions that will be parsed
# each may have a '_byline' and '_text' node
OPINION_TYPES = ['opinion', 'dissent', 'concurrence']


def parse_file(file_path, court_fallback=''):
    """Parses a file, turning it into a correctly formatted dictionary, ready to
    be used by a populate script.

    :param file_path: A path the file to be parsed.
    :param court_fallback: A string used as a fallback in getting the court
    object. The regexes associated to its value in special_regexes will be used.
    """
    raw_info = get_text(file_path)
    info = {}
    # throughout the process, collect all info about judges and at the end use
    # it to populate info['judges']
    judge_info = []
    # get basic info
    info['unpublished'] = raw_info['unpublished']
    info['file'] = os.path.splitext(os.path.basename(file_path))[0]
    info['docket'] = ''.join(raw_info.get('docket', [])) or None
    info['citations'] = raw_info.get('citation', [])
    info['attorneys'] = ''.join(raw_info.get('attorneys', [])) or None
    info['posture'] = ''.join(raw_info.get('posture', [])) or None
    info['court_id'] = get_court_object(''.join(raw_info.get('court', [])),
                                        court_fallback) or None
    if not info['court_id']:
        raise Exception('Failed to find a court ID for "%s".' %
                        ''.join(raw_info.get('court', [])))

    # get the full panel text and extract judges from it
    panel_text = ''.join(raw_info.get('panel', []))
    if panel_text:
        judge_info.append(('Panel\n-----', panel_text))
    info['panel'] = find_judge_names(panel_text) or []
    # get dates
    dates = raw_info.get('date', []) + raw_info.get('hearing_date', [])
    info['dates'] = parse_dates(dates)
    # get case names
    info['case_name_full'] = format_case_name(''.join(raw_info.get('caption', []))) or None
    info['case_name'] = format_case_name(''.join(raw_info.get('reporter_caption', []))) or None
    info['case_name_short'] = CASE_NAME_TWEAKER.make_case_name_short(info['case_name']) or None

    # figure out if this case was heard per curiam by checking the first chunk
    # of text in fields in which this is usually indicated
    info['per_curiam'] = False
    first_chunk = 1000
    for opinion in raw_info.get('opinions', []):
        if 'per curiam' in opinion['opinion'][:first_chunk].lower():
            info['per_curiam'] = True
            break
        if opinion['byline'] and 'per curiam' in opinion['byline'][:first_chunk].lower():
            info['per_curiam'] = True
            break

    # condense opinion texts if there isn't an associated byline
    # print a warning whenever we're appending multiple texts together
    info['opinions'] = []
    for current_type in OPINION_TYPES:
        last_texts = []
        for opinion in raw_info.get('opinions', []):
            if opinion['type'] != current_type:
                continue
            last_texts.append(opinion['opinion'])
            if opinion['byline']:
                judge_info.append((
                    '%s Byline\n%s' % (current_type.title(), '-' * (len(current_type) + 7)),
                    opinion['byline']
                ))
                # add the opinion and all of the previous texts
                judges = find_judge_names(opinion['byline'])
                info['opinions'].append({
                    'opinion': '\n'.join(last_texts),
                    'opinion_texts': last_texts,
                    'type': current_type,
                    'author': judges[0] if judges else None,
                    'joining': judges[1:] if len(judges) > 0 else [],
                    'byline': opinion['byline'],
                })
                last_texts = []

        # if there are remaining texts without bylines, either add them to the
        # last opinion of this type, or if there are none, make a new opinion
        # without an author
        if last_texts:
            relevant_opinions = [o for o in info['opinions'] if o['type'] == current_type]
            if relevant_opinions:
                relevant_opinions[-1]['opinion'] += '\n%s' % '\n'.join(last_texts)
                relevant_opinions[-1]['opinion_texts'].extend(last_texts)
            else:
                info['opinions'].append({
                    'opinion': '\n'.join(last_texts),
                    'opinion_texts': last_texts,
                    'type': current_type,
                    'author': None,
                    'joining': [],
                    'byline': '',
                })

    # check if opinions were heard per curiam by checking if the first chunk of
    # text in the byline or in any of its associated opinion texts indicate this
    for opinion in info['opinions']:
        # if there's already an identified author, it's not per curiam
        if opinion['author'] > 0:
            opinion['per_curiam'] = False
            continue
        # otherwise, search through chunks of text for the phrase 'per curiam'
        per_curiam = False
        first_chunk = 1000
        if 'per curiam' in opinion['byline'][:first_chunk].lower():
            per_curiam = True
        else:
            for text in opinion['opinion_texts']:
                if 'per curiam' in text[:first_chunk].lower():
                    per_curiam = True
                    break
        opinion['per_curiam'] = per_curiam

    # construct the plain text info['judges'] from collected judge data
    info['judges'] = '\n\n'.join('%s\n%s' % i for i in judge_info)

    # Add the same sha1 value to every opinion (multiple opinions can come from
    # a single XML file).
    sha1 = get_sha1(file_path)
    for opinion in info['opinions']:
        opinion['sha1'] = sha1

    return info


def get_sha1(file_path):
    """Calculate the sha1 of a file at a given path."""
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def get_text(file_path):
    """Reads a file and returns a dictionary of grabbed text.

    :param file_path: A path the file to be parsed.
    """
    with open(file_path, 'r') as f:
        file_string = f.read()
    raw_info = {}

    # used when associating a byline of an opinion with the opinion's text
    current_byline = {'type': None, 'name': None}

    # if this is an unpublished opinion, note this down and remove all
    # <unpublished> tags
    raw_info['unpublished'] = False
    if '<opinion unpublished=true>' in file_string:
        file_string = file_string.replace('<opinion unpublished=true>', '<opinion>')
        file_string = file_string.replace('<unpublished>', '').replace('</unpublished>', '')
        raw_info['unpublished'] = True

    # turn the file into a readable tree
    try:
        root = ET.fromstring(file_string)
    except ET.ParseError:
        # these seem to be erroneously swapped quite often -- try to fix the
        # misordered tags
        file_string = file_string.replace('</footnote_body></block_quote>',
                                          '</block_quote></footnote_body>')
        root = ET.fromstring(file_string)
    for child in root.iter():
        # if this child is one of the ones identified by SIMPLE_TAGS, just grab
        # its text
        if child.tag in SIMPLE_TAGS:
            # strip unwanted tags and xml formatting
            text = get_xml_string(child)
            for r in STRIP_REGEX:
                text = re.sub(r, '', text)
            text = re.sub(r'<.*?>', ' ', text).strip()
            # put into a list associated with its tag
            raw_info.setdefault(child.tag, []).append(text)
            continue
        for opinion_type in OPINION_TYPES:
            # if this child is a byline, note it down and use it later
            if child.tag == "%s_byline" % opinion_type:
                current_byline['type'] = opinion_type
                current_byline['name'] = get_xml_string(child)
                break
            # if this child is an opinion text blob, add it to an incomplete
            # opinion and move into the info dict
            if child.tag == "%s_text" % opinion_type:
                # add the full opinion info, possibly associating it to a byline
                raw_info.setdefault('opinions', []).append({
                    'type': opinion_type,
                    'byline': current_byline['name'] if current_byline['type'] == opinion_type else None,
                    'opinion': get_xml_string(child)
                })
                current_byline['type'] = current_byline['name'] = None
                break
    return raw_info


def get_xml_string(e):
    """Returns a normalized string of the text in <element>.

    :param e: An XML element.
    """
    inner_string = re.sub(r'(^<%s\b.*?>|</%s\b.*?>$)' % (e.tag, e.tag), '', ET.tostring(e))
    return  inner_string.decode('utf-8').strip()


def parse_dates(raw_dates):
    """Parses the dates from a list of string.
    Returns a list of lists of (string, datetime) tuples if there is a string before the date (or None).

    :param raw_dates: A list of (probably) date-containing strings
    """
    months = re.compile("january|february|march|april|may|june|july|august|september|october|november|december")
    dates = []
    for raw_date in raw_dates:
        # there can be multiple years in a string, so we split on possible indicators
        raw_parts = re.split('(?<=[0-9][0-9][0-9][0-9])(\s|.)', raw_date)
        #index over split line and add dates
        inner_dates = []
        for raw_part in raw_parts:
            # consider any string without either a month or year not a date
            no_month = False
            if re.search(months, raw_part.lower()) is None:
                no_month = True
                if re.search('[0-9][0-9][0-9][0-9]', raw_part) is None:
                    continue
            # strip parenthesis from the raw string (this messes with the date parser)
            raw_part = raw_part.replace('(', '').replace(')', '')
            # try to grab a date from the string using an intelligent library
            try:
                date = dparser.parse(raw_part, fuzzy=True).date()
            except:
                continue
            # split on either the month or the first number (e.g. for a 1/1/2016 date) to get the text before it
            if no_month:
                text = re.compile('(\d+)').split(raw_part.lower())[0].strip()
            else:
                text = months.split(raw_part.lower())[0].strip()
            # remove footnotes and non-alphanumeric characters
            text = re.sub('(\[fn.?\])', '', text)
            text = re.sub('[^A-Za-z ]', '', text).strip()
            # if we ended up getting some text, add it, else ignore it
            if text:
                inner_dates.append((clean_string(text), date))
            else:
                inner_dates.append((None, date))
        dates.append(inner_dates)
    return dates


def format_case_name(n):
    """Applies standard harmonization methods after normalizing with lowercase."""
    return titlecase(harmonize(n.lower()))


def get_court_object(raw_court, fallback=''):
    """Get the court object from a string. Searches through `state_pairs`.

    :param raw_court: A raw court string, parsed from an XML file.
    :param fallback: If fail to find one, will apply the regexes associated to this key in `SPECIAL_REGEXES`.
    """
    # this messes up for, e.g. 'St. Louis', but works for all others
    if '.' in raw_court and 'St.' not in raw_court:
        j = raw_court.find('.')
        raw_court = raw_court[:j]
    # we need the comma to successfully match Superior Courts, the name of which comes after the comma
    if ',' in raw_court and 'Superior Court' not in raw_court:
        j = raw_court.find(',')
        raw_court = raw_court[:j]
    for regex, value in state_pairs:
        if re.search(regex, raw_court):
            return value
    if fallback in SPECIAL_REGEXES:
        for regex, value in SPECIAL_REGEXES[fallback]:
            if re.search(regex, raw_court):
                return value
    if fallback in FOLDER_DICT:
        return FOLDER_DICT[fallback]


if __name__ == '__main__':
    parsed = parse_file('/vagrant/flp/columbia_data/opinions/01910ad13eb152b3.xml')
    pass
