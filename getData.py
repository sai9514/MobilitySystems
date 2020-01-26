import csv
import sqlite3
from datetime import datetime
import time
from operator import itemgetter
import geopy.distance
import networkx as nx
import matplotlib.pyplot as plt
import random

dir_db = '/home/sai/PycharmProjects/BerlinRoutes/gtfs_berlin.db'


def getNWFromAgencyEdgeAttrs(agencies):
    conn = sqlite3.connect(dir_db)
    G = nx.MultiDiGraph()
    node_attrs = {}
    for agency in agencies:
        cursor = conn.cursor()
        cursor.execute("SELECT t1.trip_id FROM trips as t1, routes as r1  WHERE r1.agency_id=? AND r1.route_id = "
                       "t1.route_id limit 100", (agency,))

        trip_rows = cursor.fetchall()
        # go through each trip and get the details of stops in that trip
        for trip_row in trip_rows:
            print("agency is: ", agency, " trip is ", trip_row)
            cursor2 = conn.cursor()
            # getting the list of stops in a trip
            cursor2.execute(
                "select s2.stop_name, r1.route_short_name, s1.arrival_time, s1.departure_time, s2.stop_lat, s2.stop_lon from "
                "stop_times as s1, stops as s2, routes as r1, trips as t1  where s1.trip_id=? AND s1.stop_id = s2.stop_id AND "
                "s1.trip_id = t1.trip_id AND t1.route_id = r1.route_id", trip_row)
            node_rows = cursor2.fetchall()

            i = 1
            while i < len(node_rows):
                # adding attributes to edges of the graph
                if not G.has_edge(node_rows[i - 1][0], node_rows[i][0], key=node_rows[i - 1][1]):
                    arr_time = getTimeFromStr(node_rows[i][2])
                    dep_time = getTimeFromStr(node_rows[i - 1][3])
                    diff_minutes = time.mktime(arr_time.timetuple()) - time.mktime(dep_time.timetuple())
                    time_taken = {node_rows[i][1]: diff_minutes}
                    G.add_edge(node_rows[i - 1][0], node_rows[i][0], key=node_rows[i - 1][1], attrs=time_taken)
                # adding coord as attributes to each node
                if node_rows[i - 1][0] not in node_attrs:
                    node_attrs[node_rows[i - 1][0]] = (node_rows[i - 1][4], node_rows[i - 1][5])
                if i == len(node_rows) - 1:
                    if node_rows[i][0] not in node_attrs:
                        node_attrs[node_rows[i][0]] = (node_rows[i][4], node_rows[i][5])
                i = i + 1

    # we have added all the public transport stops in the above for loop

    print("No. of edges with only public transport: ", nx.number_of_edges(G))

    nodeDegrees = list(G.degree())

    # to get no. of e scooters based on no. of nodes always between 60% to 20 %
    # 0.2 + 0.45×2^(-0.01×n×n)
    eScooterNo = int(0.2 * len(nodeDegrees))
    print("EScooter Nos: ", eScooterNo)

    # sorting the nodes based on highest degrees to place e scooters near them
    sortedNodes = sorted(nodeDegrees, key=itemgetter(1), reverse=True)
    print(sortedNodes)

    # creating links between stops and e scooters
    choiceSet = [-1, 1]
    i = 0
    extraCoords = {}
    for i in range(0, eScooterNo):
        eScooterCoord = (float("{:6f}".format(float(node_attrs[sortedNodes[i][0]][0]))) + (
                random.choice(choiceSet) * float('0.0000300')),
                         float("{:6f}".format(float(node_attrs[sortedNodes[i][0]][1]))) + (
                                 random.choice(choiceSet) * float('0.0000300')))
        extraCoords['es_' + str(i)] = eScooterCoord
        for item in node_attrs.items():
            d = geopy.distance.vincenty(eScooterCoord, item[1]).km
            if d < 0.5:
                G.add_edge('es_' + str(i), item[0], key='scoot', attrs={"scoot": int(180 * d)})
                G.add_edge(item[0], 'es_' + str(i), key='walk', attrs={"walk": int(720 * d)})
            elif 0.5 <= d <= 5:
                G.add_edge('es_' + str(i), item[0], key='scoot', attrs={"scoot": int(180 * d)})
        print("EScooter Coord: ", eScooterCoord, " added!")
        print(eScooterNo - i - 1, " EScooters left")
        i = i + 1

    node_attrs.update(extraCoords)

    nx.set_node_attributes(G, name='locale', values=node_attrs)

    print("No. of edges after stops and e scooters: ", nx.number_of_edges(G))

    # locale_attrs = nx.get_node_attributes(G, 'locale')
    # print(locale_attrs.items())
    # edge_attrs = nx.get_edge_attributes(G, 'attrs')
    # print(edge_attrs.items())
    nx.draw_networkx(G, with_labels=True, node_size=10, font_size=2, arrowsize=4)
    nx.write_gpickle(G, "/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlin.gpickle")
    plt.savefig("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/publicTransport.pdf", bbox_inches='tight',
                format='pdf', dpi=1200)
    return True


def getUserWeeklyTripDetails():
    with open('userData.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        user_weekly_trips = {
            "week1": [],
            "week2": [],
            "week3": [],
            "week4": []
        }
        header = next(csv_reader)
        for row in csv_reader:
            weeks = row[8:]
            print(weeks)
            i = 0
            for week in weeks:
                if i == 0:
                    if int(week) == 1:
                        user_weekly_trips["week1"].append((row[3], row[4]))
                if i == 1:
                    if int(week) == 1:
                        user_weekly_trips["week2"].append((row[3], row[4]))
                if i == 2:
                    if int(week) == 1:
                        user_weekly_trips["week3"].append((row[3], row[4]))
                if i == 3:
                    if int(week) == 1:
                        user_weekly_trips["week4"].append((row[3], row[4]))
                i += 1
    return user_weekly_trips


def getUserMonthlyTripDetails():
    with open('userData.csv') as csv_file:
        user_monthly_trips = []
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)
        for row in csv_reader:
            weeks = row[8:]
            i = 0
            for week in weeks:
                if i == 0:
                    if int(week) == 1:
                        user_monthly_trips.append((row[3], row[4]))
                if i == 1:
                    if int(week) == 1:
                        user_monthly_trips.append((row[3], row[4]))
                if i == 2:
                    if int(week) == 1:
                        user_monthly_trips.append((row[3], row[4]))
                if i == 3:
                    if int(week) == 1:
                        user_monthly_trips.append((row[3], row[4]))
                i += 1
    return user_monthly_trips


def getTimeFromStr(time_str):
    if int(time_str.split(':')[0]) >= 24:
        new_str = int(time_str[:2]) - 24
        new_time_str = str(new_str) + ":" + time_str.split(':', 1)[1]
        time_str = "2000:01:01:" + new_time_str
    else:
        time_str = "2000:01:01:" + time_str
    trip_time = datetime.strptime(time_str, '%Y:%m:%d:%H:%M:%S')
    return trip_time


"""
def getTripsFromStop(stop_id, stop_time):
    conn = sqlite3.connect('gtfs_berlin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stop_times where stop_id=?", [stop_id])
    rows = cursor.fetchall()
    current_time = datetime.strptime(stop_time, '%H:%M:%S')
    trips = []

    for row in rows:
        trip_time = getTimeFromStr(row[2])
        diff_minutes = time.mktime(trip_time.timetuple()) - time.mktime(current_time.timetuple())
        if diff_minutes in range(0, 900):
            print(row[0])
            print(trip_time, "\n")
            trips.append(row[0])
    return trips
"""


def getClosestStops(lat, lon, dist):
    conn = sqlite3.connect(dir_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stops")
    rows = cursor.fetchall()
    init_coord = (lat, lon)
    close_stops = []
    print("Inside getClosestStops")
    for row in rows:
        stop_coord = (row[4], row[5])
        if geopy.distance.vincenty(stop_coord, init_coord).km < dist:
            close_stops.append(row[0])
    return close_stops


def getNWFromAgencyNodeAttrs(agency):
    conn = sqlite3.connect(dir_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT t1.trip_id FROM trips as t1, routes as r1  WHERE r1.agency_id=1 AND r1.route_id = t1.route_id limit 500")
    trip_rows = cursor.fetchall()
    G = nx.MultiDiGraph()
    attrs = {}

    for trip_row in trip_rows:
        cursor2 = conn.cursor()
        cursor2.execute("select s2.stop_name, r1.route_short_name, s1.arrival_time, s1.departure_time from stop_times "
                        "as s1, stops as s2, routes as r1, trips as t1  where s1.trip_id=? AND s1.stop_id = "
                        "s2.stop_id AND s1.trip_id = t1.trip_id AND t1.route_id = r1.route_id", trip_row)
        node_rows = cursor2.fetchall()
        for node_row in node_rows:
            if node_row[0] in attrs:  # Check if the stop_name is there in the keys of the dict attrs
                if node_row[1] in attrs[node_row[0]]:  # Check if route_name's there in keys of dict attrs(stop_name)
                    temp = attrs[node_row[0]][node_row[1]]  # Since routename is already there, append the arr,dep time
                    temp.append((node_row[2], node_row[3]))
                    attrs[node_row[0]][node_row[1]] = temp
                else:
                    attrs[node_row[0]][node_row[1]] = [(node_row[2], node_row[
                        3])]  # Since routename is not there, add routename as key and also initial arr,dep time
            else:
                attrs[node_row[0]] = {node_row[1]: [(node_row[2], node_row[
                    3])]}  # Since stop name is not there, add stopname as key and add the value of this key as dict
        i = 1
        while i < len(node_rows):
            if not G.has_edge(node_rows[i - 1][0], node_rows[i][0]):
                G.add_edge(node_rows[i - 1][0], node_rows[i][0])
            i = i + 1

    print("List of nodes are:")
    for node in nx.nodes(G):
        print(node)

    print("No. of edges: ", nx.number_of_edges(G))
    print("Attribute Dict: ", attrs)
    nx.set_node_attributes(G, name='train_times', values=attrs)
    print(nx.shortest_path(G, source='S+U Wittenau (Berlin)', target='S Anhalter Bahnhof (Berlin)'))

    # nx.draw_networkx(G, with_labels=True, node_size=10, font_size=2, arrowsize=4)
    # plt.savefig("./sample2.pdf", bbox_inches='tight', format='pdf', dpi=1200)
    return G
