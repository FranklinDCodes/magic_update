
import os
import sys
import sympy
import json
from natsort import natsorted
import json
from platformdirs import user_data_dir, user_config_dir


ESCAPES = {
    '*SPACE': ' ',
    '*LT': '<',
    '*GT': '>',
    '*LTE': '<=',
    '*GTE': '>='
}


DEF_FILE_NAME = "definitions.json"


# update functions

def default_json_update(filepath, key_str, pattern, i):

    # get value setup
    new_value, is_error = build_from_pattern(pattern, i)
    if is_error:
        return True
    
    # get key setup
    key_seq_list = key_str.split('.')
    key_str_pretty = '[' + ']['.join(key_seq_list) + ']'

    # load
    with open(filepath, 'r') as fl:
        json_file = json.load(fl)

    # key as deep as required to find lowest dict
    current_dict = json_file
    for key in key_seq_list[:-1]:
        current_dict = current_dict.setdefault(key, {})
    
    # grab old value and assign
    old_value = current_dict.get(key_seq_list[-1], "DNE")
    current_dict[key_seq_list[-1]] = new_value

    with open(filepath, 'w') as fl:

        json.dump(json_file, fl, indent=4)

    if old_value != new_value:

        print(f"\033[32mUPDATED\033[0m | {filepath} {key_str_pretty}:  {old_value} -> {new_value}")

    return False

def filename_update(filepath, pattern, idx):

    # create new filename
    new_filename, is_error = build_from_pattern(pattern, idx)
    if is_error:
        return True

    # create renamed path
    l_split_path = list(os.path.split(filepath))
    l_split_path[-1] = new_filename
    str_new_path = os.path.join(*l_split_path)

    # check for file extension
    if len(str_new_path.split('.')) == 1 and len(filepath.split('.')) > 1:

        str_new_path += '.' + filepath.split('.')[-1]

    if filepath.split('.')[-1] != 'json' and os.path.normcase(filepath) != os.path.normcase(str_new_path):
        print(f"\033[91mWARNING\033[0m | {filepath} is not a json file and was not renamed.")
        return False

    # update
    os.rename(filepath, str_new_path)

    if os.path.normcase(filepath) != os.path.normcase(str_new_path):
        print(f"\033[34mRENAMED\033[0m | {filepath} -> {str_new_path}")

    return False

def delete_key(filepath, key_str, idx):

    # load
    with open(filepath, 'r') as fl:
        json_file = json.load(fl)

    # get key setup
    key_seq_list = key_str.split('.')
    key_str_pretty = '[' + ']['.join(key_seq_list) + ']'

    # key as deep as required to find lowest dict
    current_dict = json_file
    for key in key_seq_list[:-1]:
        current_dict = current_dict.setdefault(key, {})

    # delete key
    old_value = current_dict.pop(key_seq_list[-1], None)

    with open(filepath, 'w') as fl:

        json.dump(json_file, fl, indent=4)

    if old_value is not None:
        print(f"\033[35mDELETED\033[0m | {filepath} {key_str_pretty}:  {old_value} -> DNE")


# parse functions

def clean_escape_chars(string: str):

    for (seq, val) in ESCAPES.items():

        string = string.replace(seq, val)

    return string

def parse_special_updates(args: list):

    # all updates get filepath and idx by default

    l_special_updates = list()

    for idx, arg in enumerate(args):

        if "FILENAME" in arg:

            l_special_updates.append((filename_update, arg[arg.find(':') + 1:]))
            args.pop(idx)

        if "DEL" in arg:

            l_special_updates.append((delete_key, arg[arg.find(':') + 1:]))
            args.pop(idx)

    return l_special_updates, args
    
def parse_args(args: list):

    updates = list()

    for arg in args:

        key = arg[:arg.find(':')]
        pattern = arg[arg.find(':') + 1:]

        updates.append((key, pattern))

    return updates

def resolve_ternary_operation(expression: str, idx: int):

    # calculate condition
    condition_end_idx = expression.find('?')
    condition_str = expression[:condition_end_idx]
    try:
        condition_expr = sympy.sympify(condition_str)
    except ValueError:
        print(f"\033[31mERROR\033[0m | The expression \"{condition_str}\" could not be parsed")
        return None, True
    condition = condition_expr.subs("x", idx)

    # get value string
    colon_idx = expression.find(':')
    if condition:
        value_str = expression[condition_end_idx + 1:colon_idx]
    else:
        value_str = expression[colon_idx + 1:]

    # calculate value
    if value_str.find("x") == -1:
        return value_str, False

    try:
        expr = sympy.sympify(value_str)
    except ValueError:
        print(f"\033[31mERROR\033[0m | The expression \"{value_str}\" could not be parsed")
        return None, True

    value = expr.subs("x", idx)

    return value, False


# keys for special keywords and puts in their patterns
def replace_keyword_definitions (expression: str):

    # read keyword def file
    def_file = definitions_file()
    try:
        with open(def_file, 'r') as fl:
            d_defs = json.load(fl)
    except FileNotFoundError:
        d_defs = dict()

    for (key, value) in d_defs.items():

        expression = expression.replace(key, value)

    return expression

# turns expression in {} into value
def resolve_expression(expression: str, i: int):

    # replace special keyword definitions
    expression = replace_keyword_definitions('[' + expression + ']')

    # get to a format sympy can handle
    str_clean_expr = expression.replace('#', 'x').replace('[', '(').replace(']', ')')

    # see if there is a conditional
    if str_clean_expr.find('?') != -1:
        return resolve_ternary_operation(str_clean_expr, i)

    try:
        expr = sympy.sympify(str_clean_expr)
    except ValueError:
        print(f"\033[31mERROR\033[0m | The expression \"{expression}\" could not be parsed")
        return None, True

    value = expr.subs("x", i)

    return value, False

# build value from pattern
def build_from_pattern(pattern: str, i: int):

    pattern_clean = clean_escape_chars(pattern)

    built_value = pattern_clean
    
    expression_start_idx = pattern_clean.find('{')
    last_idx = 0
    while expression_start_idx != -1:

        # ensure closing bracket
        if pattern_clean.find('}', expression_start_idx + 1) == -1:
            print("\033[31mERROR\033[0m | Closing bracket not found in pattern")
            return None, True

        str_expr = pattern_clean[expression_start_idx + 1: pattern_clean.find('}', expression_start_idx + 1)]

        value, is_error = resolve_expression(str_expr, i)

        if is_error:
            return None, True

        built_value = built_value.replace('{' + str_expr + '}', str(value))

        last_idx = expression_start_idx
        expression_start_idx = pattern_clean.find('{', last_idx + 1)

    try:
        coerced_value = json.loads(built_value)
    except json.JSONDecodeError:
        coerced_value = built_value

    return coerced_value, False

# loads directory
def get_files(dir):

    try:
        dir_files = list(os.listdir(dir))
        dir_files = natsorted(dir_files)
    except FileNotFoundError:
        print(f"\033[31mERROR\033[0m | The directory \"{dir}\" could not be found")
        return None, True
    
    return dir_files, False


# function to create the definitions file if it doesn't exist and return the path
def definitions_file() -> str:

    app_name = "MagicUpdate"
    app_author = "FranklinDoaneDev"

    # make dir
    data_path = user_data_dir(app_name, app_author)
    os.makedirs(os.path.split(os.path.join(data_path, DEF_FILE_NAME))[0], exist_ok=True)

    return os.path.join(data_path, DEF_FILE_NAME)

# basically alternate main function if magic_update define is run
def define() -> int:

    def_path = definitions_file()

    # read definitions file
    # check if non existent
    try:
        with open(def_path, 'r') as fl:
            d_defs = json.load(fl)
    except FileNotFoundError:
        d_defs = dict()

    # check that at least 1 def was passed
    if len(sys.argv) < 3:
        print("Must pass at least 1 definition")
        return -1

    # parse definitions
    lt_parsed = parse_args(sys.argv[2:])

    # check if they exist
    lt_add = list()
    for (keyword, pattern) in lt_parsed:

        # if word already has def
        if keyword in d_defs:

            # grab previous def and ask user if they want to overwrite it
            prev_def = d_defs[keyword]
            print(f"\nThe keyword {keyword} is already defined as {prev_def}.")
            ow_input = input("Would you like to overwrite it? [Y/n] ")

            # overwrite
            if ow_input.strip().lower() != 'n':
                lt_add.append((keyword, pattern))

        else:
            lt_add.append((keyword, pattern))

    # add 
    for (keyword, pattern) in lt_add:
        d_defs[keyword] = pattern

        # print
        print(f"\033[93mDEFINED\033[00m | {keyword} = {pattern}")

    # write
    with open(def_path, 'w') as fl:
        json.dump(d_defs, fl)

    return 0

def main() -> int:
    
    # check if defining
    if sys.argv[1] == "define":
        return define()

    # error handling
    if len(sys.argv) < 3:
        print("Must pass directory and at least 1 update as positional argument")
        return -1

    # get directory
    directory = sys.argv[1]
    dir_files, is_error = get_files(directory)
    if is_error:
        return -1

    # parse updates
    l_special_updates, l_other_args = parse_special_updates(sys.argv[2:])
    l_updates = parse_args(l_other_args)

    # run special updates
    for func, pattern in l_special_updates:
        for idx, filename in enumerate(dir_files):

            # check if path is more specific than current
            if directory != '.':
                filepath = os.path.join(directory, filename)
            else:
                filepath = filename
            
            # run func and check for error
            is_error = func(filepath, pattern, idx + 1)
            if is_error:
                return -1
        
        # reset dir files incase renamed
        dir_files, is_error = get_files(directory)
        if is_error:
            return -1

    # run json updates
    for key, pattern in l_updates:
        for idx, filename in enumerate(dir_files):

            if directory != '.':
                filepath = os.path.join(directory, filename)
            else:
                filepath = filename
            
            is_error = default_json_update(filepath, key, pattern, idx + 1)

            if is_error:
                return -1
            
    return 0


if __name__ == "__main__":

    main()
