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
                 
