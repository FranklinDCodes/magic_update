
import os
import sys
import sympy
import json
from natsort import natsorted


ESCAPES = {
    '\s': ' '
}


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
    
def parse_updates(args: list):

    updates = list()

    for arg in args:

        key = arg[:arg.find(':')]
        pattern = arg[arg.find(':') + 1:]

        updates.append((key, pattern))

    return updates

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

        # get to a format sympy can handle
        str_clean_expr = str_expr.replace('#', 'x')

        try:
            expr = sympy.sympify(str_clean_expr)
        except ValueError:
            print(f"\033[31mERROR\033[0m | The expression \"{str_expr}\" could not be parsed")
            return None, True
    
        value = expr.subs("x", i)

        built_value = built_value.replace('{' + str_expr + '}', str(value))

        last_idx = expression_start_idx
        expression_start_idx = pattern_clean.find('{', last_idx + 1)

    try:
        coerced_value = json.loads(built_value)
    except json.JSONDecodeError:
        coerced_value = built_value

    return coerced_value, False


def get_files(dir):

    try:
        dir_files = list(os.listdir(dir))
        dir_files = natsorted(dir_files)
    except FileNotFoundError:
        print(f"\033[31mERROR\033[0m | The directory \"{dir}\" could not be found")
        return None, True
    
    return dir_files, False


def main() -> int:

    # error handling
    if len(sys.argv) < 3:
        print("Must pass directory and at least 1 update as positional arguments")
        return -1

    # get directory
    directory = sys.argv[1]
    dir_files, is_error = get_files(directory)
    if is_error:
        return -1

    # parse updates
    l_special_updates, l_other_args = parse_special_updates(sys.argv[2:])
    l_updates = parse_updates(l_other_args)

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
