import pandas as pd
from fuzzywuzzy import fuzz
import re
import os
import string
import math

# For the university name that contains second level school/college name, parse the school/college name
def strip_school(name, best_partial_ratio_match):
    s_name = name.lower()
    s_match = best_partial_ratio_match.lower()
    start = s_name.find(s_match)
    end = start + len(s_match)
    school = (name[0:start] + name[end:len(name)]).strip()
    school = sanitize_school(school).lower()

    if 'at ' in school or ' at' in school:
        school = school.replace(' at',' ')
        school = school.replace('at ',' ')
    if ' the' in school:
        school = school.replace('the','')
    if '  ' in school:
        school = school.replace('  ','')
    school = school.replace('(','')
    school = school.replace(')','')

    # Creates a map of university names and their potential school name in the with a defined subset file from school_types.csv
    # If there exists a school with the same university and school name, it changes the school to that name, if not, it saves the name
    if s_match in university_map:
        if len(school) > 0:
            for school_type in s_types:
                if school_type in school:
                    if school_type in university_map[s_match]:
                        school = university_map[s_match][school_type]
                        break
                    else:
                        university_map[s_match][school_type] = school
    else:
        university_map[s_match] = {}
        if len(school) > 0:
            for school_type in s_types:
                if school_type in school:
                    university_map[s_match][school_type] = school
                    break
    #print(school)
    return school.strip()

# For second level school/college that's parsed from original university name, do a little clean up
def sanitize_school(school_name):
    if school_name in s_types.unique():
        return school_name + " school"
    if school_name.lower().find('school') == -1 and school_name.lower().find('college') == -1 and school_name.lower().find('center') == -1:
        return ''
    regex = re.compile('()[-,\.!?]')
    school_name = regex.sub('', school_name).strip()
    school_name = re.sub('\s+',' ', school_name)
    return school_name

# Pre-process to clean up the unversity name
def sanitize_name(name):
    # lower case, trimmed
    name = name.strip().lower()

    # remove "The" at the beginning
    if name.startswith("the "):
        name = name[4:len(name)]
    name = re.sub('\s+',' ', name)

    # replace acronyms
    namesplit = name.split()
    firstword = namesplit[0]
    if firstword in acronyms and name.find(acronyms[firstword].lower()) == -1:
        name = acronyms[firstword]
        if len(namesplit) > 1:
            name = name + ' ' + ' '.join(namesplit[1:])
        #print(f"replaced by acronym: {name}")
    return name

# Perform the match for a university
# First match using special match rules. If there is no special match for the name, use fuzzy match
def match(name, loc):
    if name in special_matches:
        value = special_matches[name]
        sanitize_rules.loc[loc] = pd.Series(
            {'orig': name, 'name': value[0], 'school': value[1], 'confidence': 'exactmatch'})
        scoreboard.loc[loc] = pd.Series({'name': name, 'best_ratio_match': value[0], 'best_ratio': 100,
                                         'best_partial_ratio_match': value[0],
                                         'best_partial_ratio': 100,
                                         'best_token_sort_ratio_match': value[0],
                                         'best_token_sort_ratio': 100})
    else:
        fuzzy_match(name, loc)

# Perform fuzzy match for each unique university name and find the best matches
# using best_ratio, best_partial_ratio, best_partial_ratio matches.
# name: a unique university name from source data set
# loc: index of the university in the list
def fuzzy_match(name, loc):
    best_ratio = 0
    best_partial_ratio = 0
    best_token_sort_ratio = 0
    best_ratio_match = ""
    best_partial_ratio_match = ""
    best_token_sort_ratio_match = ""
    # pre-process the name
    cleaned_name = sanitize_name(name)
    # go through all the universities in the world to find the best fuzzy match
    for u_name in all_school_names:
        cleaned_u_name = u_name.strip().lower()
        # cleaned_name: university name from source data
        # cleaned_u_name: university name from all universities list
        ratio = fuzz.ratio(cleaned_name.lower(), cleaned_u_name)
        partial_ratio = fuzz.partial_ratio(cleaned_name.lower(), cleaned_u_name)
        token_sort_ratio = fuzz.token_set_ratio(cleaned_name.lower(), cleaned_u_name)

        # find the best one and save it while looping through all universities
        if ratio > best_ratio:
            best_ratio = ratio
            best_ratio_match = u_name
        if partial_ratio > best_partial_ratio:
            best_partial_ratio = partial_ratio
            best_partial_ratio_match = u_name
        if token_sort_ratio > best_token_sort_ratio:
            best_token_sort_ratio = token_sort_ratio
            best_token_sort_ratio_match = u_name

        # if ratio is 100, that's the best, we don't need to continue
        if ratio == 100:
            break

    #print(name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio)
    # based on the value of the three different matches, pick one match as our replacement
    sanitize_rules.loc[loc] = decision(name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio)
    # save the best match ratios for the name in scoreboard data set
    scoreboard.loc[loc] = pd.Series({'name':name, 'best_ratio_match':best_ratio_match, 'best_ratio':best_ratio, 'best_partial_ratio_match':best_partial_ratio_match,
                                     'best_partial_ratio': best_partial_ratio, 'best_token_sort_ratio_match': best_token_sort_ratio_match, 'best_token_sort_ratio': best_token_sort_ratio})


# Based on different fuzzy match, best_ratio, best_partial_ratio, best_token_sort_ratio, pick one to use as replacement
# Output is the sanitization/replacement rules that will be applied to original source data set
# The decision values can be tuned if necessary
def decision(name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio):
    # if best_ratio value is >= 95, we will use the name matched by best_ratio
    if best_ratio >= 95:
        sanitized_row = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': 'high'})
    # if best_partial_ratio or best_token_sort_ratio match is 100,
    # and the matched university name is a partial name of the original university in source data
    # we'll try to parse the rest of the string as a college or school of the university
    elif (best_partial_ratio == 100 and best_partial_ratio_match.strip().lower() in cleaned_name.strip().lower()) or \
            (best_token_sort_ratio == 100 and best_token_sort_ratio_match.strip().lower() in cleaned_name.strip().lower()):
        sanitized_row = pd.Series({
            'orig': name,
            'name': best_partial_ratio_match if best_partial_ratio == 100 else best_token_sort_ratio_match,
            'school': strip_school(cleaned_name, best_partial_ratio_match if best_partial_ratio == 100 else best_token_sort_ratio_match),
            'confidence': 'high'})
    else:
        # matches with less confidence, but still replace, confidence value also indicates the type of match and its match ratio value
        if best_ratio > 92:
            sanitized_row = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': f'ratio-{best_ratio}'})
        elif best_partial_ratio > 95:
            sanitized_row = pd.Series({'orig': name, 'name': best_partial_ratio_match, 'school': '', 'confidence': f'partial-{best_partial_ratio}'})
        elif best_token_sort_ratio > 95:
            sanitized_row = pd.Series(
                {'orig': name, 'name': best_token_sort_ratio_match, 'school': '', 'confidence': f'token-{best_token_sort_ratio}'})
        elif best_ratio_match == best_partial_ratio_match and best_ratio_match == best_token_sort_ratio_match:
            sanitized_row = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': 'same-name'})
        else:
        # confidence is low and we'll not replace the original university name in the source data
            sanitized_row = pd.Series(
                {'orig': name, 'name': name, 'school': '', 'confidence': 'not changed'})

    return sanitized_row

# read in all university names into all_world_names data frame
def read_all_schools():
    all_world = pd.read_csv(f"{dir_path}/data/world-universities.csv", header=None)
    all_world_names = all_world[1]
    return all_world_names

# read in all acronyms into acronyms data frame
def read_acronyms():
    acronyms_df = pd.read_csv(f"{dir_path}/data/acronym.csv", usecols=['acronym', 'fullname'])
    acronyms = dict(zip(acronyms_df.acronym, acronyms_df.fullname))
    return acronyms


# read in all special match rules into special_matches data frame, where
# orig: original university name
# name: replacement university name
# school: parsed school such as business school
def read_special_matches():
    special_match_df = pd.read_csv(f"{dir_path}/data/special_match.csv", usecols=['orig','name','school'])
    special_matches = {k: (v1, v2) for k, v1, v2 in zip(special_match_df.orig, special_match_df.name, special_match_df.school)}
    return special_matches


def read_school_types():
    school_types_df = pd.read_csv(f"{dir_path}/data/school_types.csv", header=None)
    school_types = school_types_df[0]
    return school_types


def harmanize_source(sanitize_rules_map):
    source = pd.DataFrame(data, columns=['newid', 'Institution of highest degree obtained'])
    updated_source = pd.DataFrame([], columns=['newid', 'Institution of highest degree obtained', 'name'])

    i = 0
    for index, row in source.iterrows():
        orig_name = row['Institution of highest degree obtained']
        if orig_name in sanitize_rules_map:
            value = sanitize_rules_map[orig_name]
            updated_source.loc[i] = pd.Series(
                    {'newid': row['newid'], 'Institution of highest degree obtained': row['Institution of highest degree obtained'],
                     'name': value[0] if str(value[1]) == 'nan' else str(value[0]) + " - " + string.capwords(str(value[1]), sep = None)})
        else:
            updated_source.loc[i] = pd.Series(
                {'newid': row['newid'],
                 'Institution of highest degree obtained': row['Institution of highest degree obtained'],
                 'name': ''})
        i += 1
    return updated_source

def harmanize_early_degrees(sanitize_rules_map):
    source = pd.DataFrame(early_degrees, columns=['newid', 'Undergrad School', 'Master\'s Degree School'])
    updated_early_degrees = pd.DataFrame([], columns=['newid', 'Undergrad', 'Master', 'Sanitized Undergrad',
                                                      'Sanitized Master'])
    i = 0
    for index, row in source.iterrows():
        orig_undergrad = row['Undergrad School']
        orig_master = row['Master\'s Degree School']
        if orig_undergrad in sanitize_rules_map:
            value = sanitize_rules_map[orig_undergrad]
            replace_undergrad = value[0] if str(value[1]) == 'nan' else str(value[0]) + " - " + string.capwords(str(value[1]), sep=None)
        else:
            replace_undergrad = ''

        if orig_master in sanitize_rules_map:
            value = sanitize_rules_map[orig_master]
            replace_master = value[0] if str(value[1]) == 'nan' else str(value[0]) + " - " + string.capwords(str(value[1]), sep=None)
        else:
            replace_master = ''

        updated_early_degrees.loc[i] = pd.Series(
            {
                'newid': row['newid'],
                'Undergrad': row['Undergrad School'],
                'Master': row['Master\'s Degree School'],
                'Sanitized Undergrad': replace_undergrad,
                'Sanitized Master': replace_master
            }
        )

        i += 1
    return updated_early_degrees

def main():
    # step 1: build mapping rules

    # Read all school names from data file
    name_list = data[['Institution of highest degree obtained']]  #pd.DataFrame(data, columns=['Institution of highest degree obtained'])
    name_list.columns = ['college']
    undergrad_list = early_degrees[['Undergrad School']] #pd.DataFrame(early_degrees, columns=['Undergrad School'])
    undergrad_list.columns = ['college']
    master_list = early_degrees[['Master\'s Degree School']] #pd.DataFrame(early_degrees, columns=['Master\'s Degree School'])
    master_list.columns = ['college']
    all_name_list = pd.concat([name_list, undergrad_list, master_list],axis=0)
    all_name_list.dropna(inplace=True)

    # Only get the unique school names to perform the match
    # The output of the matches will be saved as a set of replacement rules in sanitize_rules
    # It will be used to replace the university names in the original source data set
    unique_name_list = all_name_list["college"].unique();

    i = 0
    for name in unique_name_list:
        # one university name is "-", skip it
        if name.strip() == '-':
            continue
        # perform the match
        match(name, i)
        i += 1

    # save scoreboard data set to csv file
    scoreboard.to_csv(f"{dir_path}/data/scoreboard.csv")
    # save santize_rules data set to csv file
    sanitize_rules.to_csv(f"{dir_path}/data/sanitize_rules.csv")

    # step 2: replace the university name based on mapping rules
    sanitize_rules_df = pd.read_csv(f"{dir_path}/data/sanitize_rules.csv", usecols=['orig', 'name', 'school'])

    sanitize_rules_map = {k: (v1, v2) for k, v1, v2 in
                          zip(sanitize_rules_df.orig, sanitize_rules_df.name, sanitize_rules_df.school)}
    updated_source = harmanize_source(sanitize_rules_map)
    updated_source.to_csv(f"{dir_path}/data/updated_source.csv")

    updated_early_degrees = harmanize_early_degrees(sanitize_rules_map)
    updated_early_degrees.to_csv(f"{dir_path}/data/updated_early_degrees.csv")


# global values
dir_path = os.path.dirname(os.path.realpath(__file__))

# read university names from source data set
data = pd.read_csv(f"{dir_path}/data/alan_highest_degree.csv")
early_degrees = pd.read_csv(f"{dir_path}/data/alan_early_degrees.csv")
# read all university names in the world
all_school_names = read_all_schools()
# all acronyms
acronyms = read_acronyms()
# read special match rules
special_matches = read_special_matches()
# data frame to save fuzzy match scores
# For each university name, we find three matched names using fuzzy match
# name: original university name
# best_ratio_match: matched university name based on best_ratio
# best_ratio: best ratio value
# best_partial_ratio_match: matched university name based on best_partial_ratio
# best_partial_ratio: best partial ratio value
# best_token_sort_ratio_match: matched university name based on best_token_sort_ratio
# best_token_sort_ratio: best token sort ratio value
scoreboard = pd.DataFrame([], columns=['name', 'best_ratio_match', 'best_ratio', 'best_partial_ratio_match', 'best_partial_ratio',
                                           'best_token_sort_ratio_match', 'best_token_sort_ratio'])
# data frame to save replacement rules
# sanitize_rules data frame is used to save replacement rules for each unique university name
# confidence: a score indicate how confident is the match
# orig: original university name
# name: replacement university name
# school: second level school/college name that is separated from original university name
sanitize_rules = pd.DataFrame([], columns=['confidence','orig', 'name', 'school'])

# data frame to create map of school names
s_types = read_school_types()
university_map = {}

# ------

main()

