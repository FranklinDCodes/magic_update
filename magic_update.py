
import os
import sys
import sympy
import json



# update functions

def default_json_update(filepath, key, pattern, i):

    new_value = build_from_pattern(pattern, i)

    with open(filepath, 'r') as fl:

        j_cfg = json.load(fl)

    old_key = str(j_cfg.get(key, "DNE"))

    j_cfg[key] = new_value

    with open(filepath, 'w') as fl:

        json.dump(new_value, fl)

    print(f"{filepath} | {old_key} -> {new_value}")

def filename_update(filepath, pattern, idx):

    # create new filename
    new_filename = build_from_pattern(pattern, idx)

    # create renamed path
    l_split_path = list(os.path.split(filepath))
    l_split_path[-1] = new_filename
    str_new_path = os.path.join(*l_split_path)

    # check for file extension
    if len(str_new_path.split('.')) == 1 and len(filepath.split('.')) > 1:

        str_new_path += filepath.split('.')[-1]

    # update
    os.rename(filepath, str_new_path)

    print(f"{filepath} -> {str_new_path}")




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

        str_expr = pattern[expression_start_idx + 1: pattern.find('}')]

        # get to a format sympy can handle
        str_clean_expr = str_expr.replace('#', 'x')

        expr = sympy.sympify(str_clean_expr)
        value = expr.subs("x", i)

        built_value = built_value.replace('{' + str_expr + '}', str(value))

        last_idx = expression_start_idx
        expression_start_idx = pattern.find('{', last_idx + 1)

    return built_value


def main():

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
            func(filepath, pattern, idx)

    # run json updates
    for key, pattern in l_updates:
        for idx, filename in enumerate(dir_files):

            filepath = os.path.join(directory, filename)
            default_json_update(filepath, key, pattern, idx)

    print("Complete.")

if __name__ == "__main__":

    main()
