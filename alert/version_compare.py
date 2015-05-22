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

def version_compare(version1, version2):
    for result in map(part_compare, version1.strip().split("."), version2.strip().split(".")):
        if result != 0: return result
    return 0

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
    print "All tests passed!"
