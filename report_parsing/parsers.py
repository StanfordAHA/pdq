# Function to create Python area dictionary from DC area report
# Key = hierarchical cell name
# Value = area

def parse_dc_area(report_name):
    tag_1 = 'Hierarchical cell'
    tag_2 = '-----'
    area_dict = {}
    report = open(report_name)
    lines = report.readlines()
    # First find hierarchical area breakdown
    for ind, line in enumerate(lines):
        if tag_1 in line:
            # Area numbers start 3 lines after tag_1
            line_num = ind + 3
            break
    for line in lines[line_num:]:
        #tag_2 marks end of area breakdown
        if tag_2 in line:
            break
        else:
            (name, area, _, _, _, _, _) = line.strip().split()
            area_dict[name] = area

    return area_dict

# Helper function to return all lines in a file that contain provided keyword

def get_keyword_lines(report_name, keyword):
    report = open(report_name)
    lines = report.readlines()
    key_lines = []
    for line in lines:
        if keyword in line:
            key_lines.append(line.strip())
    return key_lines

                 
# Function to create Python slack time dictionary from DC timing report
# Key1 = Startpoint
# Key2 = Endpoint
# Value = Slack

def parse_dc_timing(report_name):
    tags = [("Startpoint: ", 1), ("Endpoint: ", 1), ("slack (", 2)]
    keywords = {}
    for tag in tags:
        lines = get_keyword_lines(report_name, tag[0])
        keywords[tag[0]] = [line.split()[tag[1]] for line in lines]
    slack_tuples = list(zip(*[keywords[tag[0]] for tag in tags]))
    return {k1 : {k2: v} for k1, k2, v in slack_tuples}

def _create_power_dict(internal, switch, leak):
    return {'int': internal, 'switch': switch, 'leak': leak}

# Function to create Python dict from ptpx power report
# Key1 = hierarchical instance name
# Key2 = power number type (int, switch, or leak)

def parse_ptpx_power(report_name):
    # First, looked for long dashed line
    tag = '-----'
    power_dict = {}
    report = open(report_name)
    lines = report.readlines()
    for ind, line in enumerate(lines):
        if tag in line:
            line_num = ind + 1
            break
    # Get top level energy numbers
    top_line = lines[line_num]
    (name, internal, switch, leak, _, _) = top_line.strip().split()
    power_dict[name] = _create_power_dict(internal, switch, leak)
    # Get all leaf inst power numbers
    hierarchy = []
    for line in lines[line_num + 1:]:
        lspaces = len(line) - len(line.lstrip())
        depth = (lspaces - 2) / 2
        (name, _, internal, switch, leak, _, _) = line.strip.split()
        hierarchy.insert(depth, name)
        # ensure we don't include anything past the current depth
        hierarchy = hierarchy[0:depth + 1]
        hier_name = '/'.join(hierarchy)
        power_dict[hier_name] = _create_power_dict(internal, switch, leak)
   
    return power_dict 
