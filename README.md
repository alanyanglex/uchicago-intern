# uchicago-intern

This is how the match and replacement are done

Step 1: 
Read in all university names from source data and get a list of unique names. We only need to perform match for each unique name.

Step 2: 
Read in all university names of the world.

Step 3:
Perform match for each unique university name against all university names of the world and find the best matches based on best_ratio, best_partial_ratio, best_token_sort_ratio. Pick one match based on the ratio values.
Once all matches are decided, save the replacement rules to a csv file. You can inspect the replacement rules to find errors or fine tune the decision rules, before apply the rules to the original source data.

Step 4:
Read in the replacement rules and apply to the original source data set.

## Data Files
#### Input Data
#####alan_highest_degree.csv :  source data set
#####world-universities.csv : downloaded from https://github.com/endSly/world-universities-csv/blob/master/world-universities.csv, moved US universities to the top.

#### Config 
- acronym.csv 
    - Defines Acronyms mappings
- special_match.csv 
    - Defines special mappings to overwrite default rules
- school_types.csv
    - Defines Types of schools or colleges

#### Intermediate Output
- sanitize_rules.csv
    - Defines the mapping rule after fuzzy match. Inspect this file to see if match is correct. Anything not correct needs to be fixed or overwritten.
- scoreboard.csv 
    - Prints different fuzzy match scores
    
#### Output
- updated_source.csv 
    - Added a mapped name column and school column on original source, mapping is based on rules defined in sanitize_rules.csv
      
