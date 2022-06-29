# uchicago-intern

## Data Files
#### Input Data
alan_highest_degree.csv

#### Config 
- acronym.csv 
    - Defines Acronyms mappings
- special_match.csv 
    - Defines special mappings to overwrite
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
      