
import os
import sys
import sympy
import json


# update functions

def default_json_update(filepath, key, pattern, i):

    new_value, is_error = build_from_pattern(pattern, i)

    if is_error:
        return True

    with open(filepath, 'r') as fl:

        j_cfg = json.load(fl)

    old_value = str(j_cfg.get(key, "DNE"))

    j_cfg[key] = new_value

    with open(filepath, 'w') as fl:

        json.dump(j_cfg, fl, indent=4)

    print(f"\033[32mUPDATED\033[0m | {filepath} [{key}]:  {old_value} -> {new_value}")

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

    print(f"\033[34mRENAMED\033[0m | {filepath} -> {str_new_path}")

    return False

# parse functions

def parse_special_updates(args: list):

    # all updates get filepath and idx by default

    l_special_updates = list()

    for idx, arg in enumerate(args):

        if "FILENAME" in arg:

            l_special_updates.append((filename_update, arg[arg.find(':') + 1:]))
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

    built_value = pattern
    
    expression_start_idx = pattern.find('{')
    last_idx = 0
    while expression_start_idx != -1:

        # ensure closing bracket
        if pattern.find('}', expression_start_idx + 1) == -1:
            print("\033[31mERROR\033[0m | Closing bracket not found in pattern")
            return None, True

        str_expr = pattern[expression_start_idx + 1: pattern.find('}')]

        # get to a format sympy can handle
        str_clean_expr = str_expr.replace('#', 'x')

        expr = sympy.sympify(str_clean_expr)
        value = expr.subs("x", i)

        built_value = built_value.replace('{' + str_expr + '}', str(value))

        last_idx = expression_start_idx
        expression_start_idx = pattern.find('{', last_idx + 1)

    return built_value, False


def main() -> int:

    # error handling
    if len(sys.argv) < 3:
        print("Must pass directory and at least 1 update as positional arguments")
        return -1

    # unpack args
    directory = sys.argv[1]
    dir_files = list(os.listdir(directory))
    dir_files.sort()
    l_special_updates, l_other_args = parse_special_updates(sys.argv[2:])
    l_updates = parse_updates(l_other_args)

    # run special updates
    for func, pattern in l_special_updates:
        for idx, filename in enumerate(dir_files):

            filepath = os.path.join(directory, filename)
            is_error = func(filepath, pattern, idx + 1)

            if is_error:
                return -1

    # run json updates
    for key, pattern in l_updates:
        for idx, filename in enumerate(dir_files):

            filepath = os.path.join(directory, filename)
            is_error = default_json_update(filepath, key, pattern, idx + 1)

            if is_error:
                return -1
            
    return 0


if __name__ == "__main__":

    main()
