import csv
import glob
import subprocess


_DEFAULT_REPORTS_DIR = "reports/"
_DEFAULT_STATS_FILENAME = "stats.csv"


def _map_op(op: str):
    if op == "or_":
        return "or"
    if op == "and_":
        return "and"
    return op


def get_stats_from_reports(reports_dir: str = _DEFAULT_REPORTS_DIR):
    dirs = glob.glob(f"{reports_dir}/reports.*")
    stats = {}
    for dir in dirs:
        label = dir[len(reports_dir) + 8:]
        labels = label.split("-")
        width = int(labels[0])
        raw_op = str(labels[1])
        clk = float(labels[2])
        op = _map_op(raw_op)
        report_filename = f"{dir}/magma_UInt_{width}_{op}_wrapper.mapped.area.rpt"
        key = "Total cell area: "
        ret = subprocess.run(["grep", key, report_filename], capture_output=True)
        area = float(ret.stdout.strip()[len(key):])
        stats[(width, op, clk)] = area
    return stats


def write_stats_to_csv(stats, stats_filename: str = _DEFAULT_STATS_FILENAME):
    with open(stats_filename, "w") as f:
        writer = csv.writer(f)
        for k, v in stats.items():
            writer.writerow(list(k) + [v])


def load_stats_from_csv(stats_filename: str = _DEFAULT_STATS_FILENAME):
    stats = {}
    with open(stats_filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            stats[tuple(row[:-1])] = row[-1]
    return stats


if __name__ == "__main__":
    stats = get_stats_from_reports()
    write_stats_to_csv(stats)
