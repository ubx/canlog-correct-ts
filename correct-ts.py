#!/usr/bin/env python3
import argparse
import datetime
import os
from statistics import mean, variance, stdev

'''
   Adjust time stamps according to to GPS time (UTC):
      sudo ip link add dev vcan0 type vcan
      sudo ip link set up vcan0
'''

parser = argparse.ArgumentParser(description='Correct time stamps according the GPS time (UTC)')
parser.add_argument('-input', metavar='input', type=str, help='Input logfile')
args = parser.parse_args()

inputFile = args.input


# (1564994147.496590) can0 78A#0A0C1CE5F7990000
def getCanDate(line):
    parts = (" ".join(line.split()).split())
    ts = float(parts[0][1:18])
    canDevStr = parts[1]
    parts2 = parts[2].split("#")

    canIdStr = parts2[0]
    nodeIdStr = parts2[1][0:2]
    dataStr = parts2[1][8:40]
    return ts, canDevStr, canIdStr, dataStr, nodeIdStr


def statistics(ids, id):
    if id not in ids:
        ids[id] = 1
    ids[id] = ids[id] + 1


## "(1564994154.769054) can0 40C#0A032A3A1BC27A49"
## "(1569437515.1000000) can0 141#0A0200A942E1CBEA" --> ERROR
def check(line):
    if not line.startswith("("):
        return False
    for c in line[1:11]:
        if not c.isdigit():
            return False
    if line[11] != '.':
        return False
    for c in line[12:18]:
        if not c.isdigit():
            return False
    if line[18] != ')':
        return False
    return True


def close_logfile():
    global new_log
    try:
        new_log.close()
        os.rename(new_log.name,
                  "data/candump-{}.log".format(datetime.datetime.fromtimestamp(int(ts_log_first))).replace(" ", "_").replace(":", ""))
    except IOError:
        pass


def print_statistics():
    global mmm
    m = mean(mmm)
    print("Mean diff ts_gps-ts =", m, "variance=", variance(mmm, m), "stdev=", stdev(mmm, m),
          "max=", max(mmm), "min=", min(mmm))
    mmm = []


with open(inputFile) as inf:
    canIds = {}
    nodeIds = {}
    lastTime = 0
    dataUtcStr = None
    dataDateStr = None
    ts_log_last = None
    ts_log_first = None
    log_file_nr = 0
    new_log = None
    diff = None
    mmm = []

    for cnt, line in enumerate(inf):
        diff = 0
        if new_log == None:
            log_file_nr = log_file_nr + 1
            new_log = open("data/newlog_{}.log".format(log_file_nr), "w+")
        if not check(line):
            print("ERROR, line={:d} {:s}".format(cnt, line))
        else:
            ts, canDevStr, canIdStr, dataStr, nodeIdStr = getCanDate(line)
            if ts_log_first == None: ts_log_first = ts
            canId = int(canIdStr, 16)

            if canId == 0x1FFFFFF0:  # Time sync
                # (1566638861.000000) can0 1FFFFFF0#1308180B1B29
                #   0.00000 1  536870896x Tx D 6  19   8  24  11  27  41
                ts_log = datetime.datetime((int(line[34:36], 16) + 2000),
                                           int(line[37:38], 16),
                                           int(line[38:40], 16),
                                           int(line[40:42], 16),
                                           int(line[42:44], 16),
                                           int(line[44:46], 16)).timestamp()
                if ts_log_last == None: ts_log_last = ts_log
                diff = ts_log - ts_log_last
                # print("Syn", datetime.datetime.fromtimestamp(ts_log), "/", ts_log - ts, "/", diff)
                ## if diff > 1.0: print("Syn diff > 1.0", diff)
                ts_log_last = ts_log
                line = None

            elif canId == 1200:  # UTC)
                if not dataDateStr == None:
                    ts_gps = datetime.datetime((int(dataDateStr[4:6], 16) * 100) + int(dataDateStr[6:8], 16),
                                               int(dataDateStr[2:4], 16),
                                               int(dataDateStr[0:2], 16), int(dataStr[0:2], 16), int(dataStr[2:4], 16),
                                               int(dataStr[4:6], 16)).timestamp()
                    # print("Gps", datetime.datetime.fromtimestamp(ts), "/", datetime.datetime.fromtimestamp(ts_gps), "/",
                    #       ts_gps - ts)
                mmm.append(ts_gps - ts)
                dataUtcStr = dataStr

            elif canId == 1206:
                dataDateStr = dataStr

        if line != None: new_log.write(line)

        if diff > 3600 * 5:
            close_logfile()
            new_log = None
            ts_log_first = None
            print_statistics()

        statistics(canIds, canId)
        statistics(nodeIds, int(nodeIdStr, 16))
        lastTime = ts

    close_logfile()
    print_statistics()

print("canId statistics")
print(sorted(canIds.items(), key=lambda kv: kv[0], reverse=True))
print(sorted(canIds.items(), key=lambda kv: kv[1], reverse=True))
print("nodeId statistics")
print(sorted(nodeIds.items(), key=lambda kv: kv[0], reverse=True))
print(sorted(nodeIds.items(), key=lambda kv: kv[1], reverse=True))
