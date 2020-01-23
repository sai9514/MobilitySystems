import sqlite3
from datetime import datetime
import time
from typing import Dict, Any
from operator import itemgetter
import decimal
import geopy.distance
import networkx as nx
import matplotlib.pyplot as plt
import random

dir_db = "C:\\Users\\jo_ma\\PycharmProjects\\Mobility\\gtfs_berlin.db"


def getTimeFromStr(time_str):
    if int(time_str.split(':')[0]) >= 24:
        new_str = int(time_str[:2]) - 24
        new_time_str = str(new_str) + ":" + time_str.split(':', 1)[1]
        time_str = "2000:01:01:" + new_time_str
        print(time_str)
    time_str = "2000:01:01:" + time_str
    print(time_str)
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


def getNWFromAgencyEdgeAttrs(agency, orig, dest):
    conn = sqlite3.connect(dir_db)
    cursor = conn.cursor()
    cursor.execute("SELECT t1.trip_id FROM trips as t1, routes as r1  WHERE r1.agency_id=? AND r1.route_id = "
                  "t1.route_id limit 10", (agency,))

    trip_rows = cursor.fetchall()
    G = nx.MultiDiGraph()
    node_attrs = {}
    # go through each trip and get the details of stops in that trip
    for trip_row in trip_rows:
        cursor2 = conn.cursor()
        # getting the list of stops in a trip
        cursor2.execute(
            "select s2.stop_name, r1.route_short_name, s1.arrival_time, s1.departure_time, s2.stop_lat, s2.stop_lon "
            "from stop_times as s1, stops as s2, routes as r1, trips as t1  where s1.trip_id=? AND s1.stop_id = "
            "s2.stop_id AND s1.trip_id = t1.trip_id AND t1.route_id = r1.route_id", trip_row)
        node_rows = cursor2.fetchall()

        i = 1
        while i < len(node_rows):
            # adding attributes to edges of the graph
            if not G.has_edge(node_rows[i - 1][0], node_rows[i][0], key=node_rows[i - 1][1]):
                arr_time = getTimeFromStr(node_rows[i][2])
                dep_time = getTimeFromStr(node_rows[i - 1][3])
                print(arr_time.timetuple())
                print(dep_time.timetuple())
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
    eScooterNo = int((0.2 + 0.45 * (2 ** (-0.01 * len(nodeDegrees)))) * len(nodeDegrees))

    # sorting the nodes based on highest degrees to place e scooters near them
    sortedNodes = sorted(nodeDegrees, key=itemgetter(1), reverse=True)
    print(sortedNodes)
    print(node_attrs)

    # creating links between orig, dest and different public transport links
    print("Distances between orig, dest and stops: ")
    for item in node_attrs.items():
        d1 = geopy.distance.vincenty(orig, item[1]).km
        d2 = geopy.distance.vincenty(dest, item[1]).km
        print(d1, d2)
        if d1 < 10:
            G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
        if d2 < 12:
            G.add_edge(item[0], "dest", key='walk', attrs={"walk": int(720 * d2)})

    # creating links between stops and e scooters
    choiceSet = [-1, 1]
    i = 0
    extraCoords = {}
    print("Distances between e scooter and stops: ")
    for i in range(0, eScooterNo):
        eScooterCoord = (float("{:6f}".format(float(node_attrs[sortedNodes[i][0]][0]))) + (
                    random.choice(choiceSet) * float('0.0000300')),
                         float("{:6f}".format(float(node_attrs[sortedNodes[i][0]][1]))) + (
                                     random.choice(choiceSet) * float('0.0000300')))
        print(eScooterCoord)
        extraCoords['es_' + str(i)] = eScooterCoord
        for item in node_attrs.items():
            d = geopy.distance.vincenty(eScooterCoord, item[1]).km
            print(d)
            if d < 5:
                G.add_edge('es_' + str(i), item[0], key='scoot', attrs={"scoot": int(300 * d)})
                G.add_edge(item[0], 'es_' + str(i), key='scoot', attrs={"scoot": int(300 * d)})
        i = i + 1

    # creating link between orig, dest and e scooters if less than a threshold
    print("Distances between orig, dest, e scooters: ")
    for item in extraCoords.items():
        d1 = geopy.distance.vincenty(orig, item[1]).km
        d2 = geopy.distance.vincenty(dest, item[1]).km
        print(d1, d2)
        if d1 < 8:
            G.add_edge("orig", item[0], key='walk', attrs={"walk": int(300 * d1)})
        if d2 < 12:
            G.add_edge(item[0], "dest", key='walk', attrs={"walk": int(300 * d2)})

    extraCoords['orig'] = orig
    extraCoords['dest'] = dest

    node_attrs.update(extraCoords)

    nx.set_node_attributes(G, name='locale', values=node_attrs)

    print("No. of edges after orig, dest and e scooters: ", nx.number_of_edges(G))

    # locale_attrs = nx.get_node_attributes(G, 'locale')
    # print(locale_attrs.items())
    # edge_attrs = nx.get_edge_attributes(G, 'attrs')
    # print(edge_attrs.items())

    nx.draw_networkx(G, with_labels=True, node_size=10, font_size=2, arrowsize=4)
    # plt.savefig("./OutputGraphs/sample1.pdf", bbox_inches='tight', format='pdf', dpi=1200)
    return G