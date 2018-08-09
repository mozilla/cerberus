import re

def parse_part(part):
    if part is None or part == "": return (0, None, 0, None)
    if part == "*": return (float("inf"),)
    match = re.match("(-?\d+)(?:(\D+)(?:(-?\d+)(?:(\D+))?)?)?", part)
    components = list(match.groups())
    components[2] = int(components[2]) if components[2] is not None else 0
    if components[1] == "+":
        return (int(components[0]) + 1, "pre", components[2], components[3])
    return (int(components[0]), components[1], components[2], components[3])

def part_compare(part1, part2):
    for component1, component2 in zip(parse_part(part1), parse_part(part2)):
        if component1 is not None and component2 is None: return -1
        if component1 is None and component2 is not None: return 1
        if component1 < component2: return -1
        if component1 > component2: return 1
    return 0

def part_to_string(part):
    part_string = str(part[0])
    if part[1] is not None:
        part_string += part[1]
        if part[2] != 0 or part[3] is not None:
            part_string += str(part[2])
            if part[3] is not None:
                part_string += part[3]
    return part_string

def version_compare(version1, version2):
    for result in map(part_compare, version1.strip().split("."), version2.strip().split(".")):
        if result != 0: return result
    return 0

def version_add_major(version, amount = 1):
    version_parts = list(map(parse_part, version.strip().split(".")))
    major = version_parts[0]
    version_parts[0] = (major[0] + amount, major[1], major[2], major[3])
    return ".".join(part_to_string(part) for part in version_parts)

def version_get_major(version):
    versions = version.strip().split(";")
    return parse_part(versions[-1].strip().split(".")[0])[0]

def version_normalize_nightly(version):
    version_parts = list(map(parse_part, version.strip().split(".")))
    if len(version_parts) == 1: return version + ".0a1" # versions of the form N
    if len(version_parts) == 2:
        minor = version_parts[1]
        if minor[0] == 0 and minor[1] is None: # versions of the form N.0
            version_parts[1] = (0, "a", 1, None)
        return ".".join(part_to_string(part) for part in version_parts)
    return version

if __name__ == "__main__":
    assert version_compare("1.-1", "1") == -1
    assert version_compare("1", "1.") == 0
    assert version_compare("1.", "1.0") == 0
    assert version_compare("1.0", "1.0.0") == 0
    assert version_compare("1.0.0", "1.1a") == -1
    assert version_compare("1.1a", "1.1aa") == -1
    assert version_compare("1.1aa", "1.1ab") == -1
    assert version_compare("1.1ab", "1.1b") == -1
    assert version_compare("1.1b", "1.1c") == -1
    assert version_compare("1.1c", "1.1pre") == -1
    assert version_compare("1.1pre", "1.1pre0") == 0
    assert version_compare("1.1pre0", "1.0+") == 0
    assert version_compare("1.0+", "1.1pre1a") == -1
    assert version_compare("1.1pre1a", "1.1pre1aa") == -1
    assert version_compare("1.1pre1aa", "1.1pre1b") == -1
    assert version_compare("1.1pre1b", "1.1pre1") == -1
    assert version_compare("1.1pre1", "1.1pre2") == -1
    assert version_compare("1.1pre2", "1.1pre10") == -1
    assert version_compare("1.1pre10", "1.1.-1") == -1
    assert version_compare("1.1.-1", "1.1") == -1
    assert version_compare("1.1", "1.1.0") == 0
    assert version_compare("1.1.0", "1.1.00") == 0
    assert version_compare("1.1.00", "1.10") == -1
    assert version_compare("1.10", "1.*") == -1
    assert version_compare("1.*", "1.*.1") == -1
    assert version_compare("1.*.1", "2.0") == -1
    assert version_add_major("42.0.1") == "43.0.1"
    assert version_add_major("42", 1000) == "1042"
    assert version_add_major("42.0") == "43.0"
    assert version_add_major("0.0.0") == "1.0.0"
    assert version_add_major("42.0a") == "43.0a"
    assert version_add_major("42.0a1") == "43.0a1"
    assert version_add_major("42.0a1b") == "43.0a1b"
    assert version_add_major("1a2b.3c4d.5e6f") == "2a2b.3c4d.5e6f"
    assert version_get_major("42.0.1") == 42
    assert version_get_major("42") == 42
    assert version_get_major("42.0") == 42
    assert version_get_major("0.0.0") == 0
    assert version_get_major("42.0a") == 42
    assert version_get_major("42.0a1") == 42
    assert version_get_major("42.0a1b") == 42
    assert version_get_major("1a2b.3c4d.5e6f") == 1
    assert version_get_major("52.9; 60.1") == 60
    assert version_normalize_nightly("42") == "42.0a1"
    assert version_normalize_nightly("42.0") == "42.0a1"
    assert version_normalize_nightly("42.0a") == "42.0a"
    assert version_normalize_nightly("42.0a1") == "42.0a1"
    assert version_normalize_nightly("42.1") == "42.1"
    print "All tests passed!"
