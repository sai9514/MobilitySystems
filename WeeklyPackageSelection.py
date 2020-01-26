import copy
from operator import itemgetter
import geopy.distance
from MobilitySystems import getData
from gurobipy import *
import networkx as nx
import csv

agency = 1
eScooterLimit = 1200
valueTime = 0.00322222222
EScooterCost = 0.003
WeeklyPackageCost = 34
ulEscoot = 1

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
print(user_weekly_trips.items())

# graph = getData.getNWFromAgencyEdgeAttrs(agency)
# if graph is True:
#     G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlin.gpickle")


for week in user_weekly_trips:  # each key is each week - includes all the trips in the week
    trips = user_weekly_trips[week]  # includes all the trips in this week
    m = Model('WeeklyPackageRoutes')
    WeeklyOverUsage = m.addVar(vtype=GRB.INTEGER, name='WeeklyOverUsage')
    edgeAttrs = {}
    publicEdgeAttrs = {}
    scootEdgeAttrs = {}
    monValTime = {}
    eScooterTime = {}
    eScooterUnlockCost = {}

    edgeIn = {}
    edgeOut = {}
    r = {}
    tripNum = 1
    tripObj = []
    nodeList = []
    mainNodesList = []
    print("no. of trips: ", len(trips))
    orig = []
    dest = []
    for trip in trips:
        G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlin1.gpickle")
        tripEdgeAttrs = {}
        tripScooterEdgeAttrs = {}
        orig.append(trip[0])
        dest.append(trip[1])
        extraCoords = {}
        node_attrs = nx.get_node_attributes(G, name='locale')

        # creating links between orig, dest and public stops and e scooter stops
        for item in node_attrs.items():
            d1 = geopy.distance.vincenty(orig[tripNum - 1], item[1]).km
            d2 = geopy.distance.vincenty(dest[tripNum - 1], item[1]).km
            if "es_" not in item[0]:  # for public transport stops
                if d1 < 1:
                    G.add_edge("orig" + str(tripNum), item[0], key='walk', attrs={"walk": int(720 * d1)})
                if d2 < 1:
                    G.add_edge(item[0], "dest" + str(tripNum), key='walk', attrs={"walk": int(720 * d2)})
            else:  # for e scooter stops
                if d1 < 1:
                    G.add_edge("orig" + str(tripNum), item[0], key='walk', attrs={"walk": int(720 * d1)})
                if d2 < 5:
                    G.add_edge(item[0], "dest" + str(tripNum), key='scoot', attrs={"scoot": int(180 * d2)})
        print("No. of edges after orig, dest and e scooters: ", nx.number_of_edges(G))
        edgeList = G.edges.data('attrs')
        nodeList.append(list(G.nodes()))
        print(*edgeList)
        # creating dictionaries with full edges and only public transport edges for different constraints
        for eachEdge in edgeList:
            edgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
            tripEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
            if 'walk' not in eachEdge[2].keys():
                if 'scoot' not in eachEdge[2].keys():
                    publicEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
                else:
                    scootEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
                    tripScooterEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]

        # key: nodes, value: list of edges entering/leaving the vertex
        edgeIn.update({(tripNum, n): [] for n in nodeList[tripNum - 1]})
        edgeOut.update({(tripNum, n): [] for n in nodeList[tripNum - 1]})

        # adding a binary variable for each link
        for edges in edgeAttrs:
            edgeLink = (edges[1][0], edges[1][1])
            u = edges[1][0]
            v = edges[1][1]
            r[tripNum, edgeLink] = m.addVar(vtype=GRB.BINARY, name='r_' + str(tripNum) + str(edgeLink))
            # print("tripNumber: ", tripNum, " u: ", u, " v: ", v)
            if (tripNum, v) in edgeIn:
                edgeIn[tripNum, v].append(r[tripNum, edgeLink])
            else:
                edgeIn[tripNum, v] = [r[tripNum, edgeLink]]
            if (tripNum, u) in edgeOut:
                edgeOut[tripNum, u].append(r[tripNum, edgeLink])
            else:
                edgeOut[tripNum, u] = [r[tripNum, edgeLink]]

        mainNodesList.append(copy.copy(nodeList[tripNum - 1]))
        print("no. of nodes in mainNOdes: ", len(mainNodesList[tripNum - 1]))
        mainNodesList[tripNum - 1].remove('orig' + str(tripNum))
        mainNodesList[tripNum - 1].remove('dest' + str(tripNum))
        print("no. of nodes in mainNOdes after removing origin and dest: ", len(mainNodesList[tripNum - 1]))

        print("No. of edges after removing orig, dest ", nx.number_of_edges(G))

        for edgeAttr in edgeAttrs:
            monValTime[tripNum, edgeAttr[1]] = int(list(edgeAttrs[edgeAttr].values())[0]) * valueTime
            # include unlock costs here
            eScooterTime[tripNum, edgeAttr[1]] = (int(list(edgeAttrs[edgeAttr].values())[0]))
            eScooterUnlockCost[tripNum, edgeAttr[1]] = ulEscoot

        with open(week + '_timings_trip_' + str(tripNum) + '.csv', 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["edges", "timings"])
            for edgeAttr in edgeAttrs:
                writer.writerow([str.encode(str(edgeAttr[1])), int(list(edgeAttrs[edgeAttr].values())[0])])

        tripObj.append(
            quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in tripEdgeAttrs.keys()) + quicksum(
            r[edgeAttr] * (eScooterUnlockCost[edgeAttr]) for edgeAttr in tripScooterEdgeAttrs.keys()))

        """
        # set Objective
        m.setObjective(tripObj, GRB.MINIMIZE)

        m.optimize()
        var_values = {}

        for v in m.getVars():
            var_values[(str.encode(v.varName))] = v.x

        print(var_values.items())

        with open('OptimumRouteTrip_' + str(tripNum) + '.csv', 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([("variables", "values")])
            for key, value in var_values.items():
                writer.writerow([key, value])
        """
        tripNum += 1
    print("value of tripNum ", tripNum)

    # adding constraints #orig
    m.addConstrs(
        (quicksum(edgeOut[t + 1, 'orig' + str(t + 1)]) - quicksum(edgeIn[t + 1, 'orig' + str(t + 1)]) == 1 for t in
         range(0, tripNum - 1)),
        name='originConst')
    m.addConstrs(
        (quicksum(edgeIn[t + 1, 'dest' + str(t + 1)]) - quicksum(edgeOut[t + 1, 'dest' + str(t + 1)]) == 1 for t in
         range(0, tripNum - 1)),
        name='destConst')

    # m.addConstrs((quicksum(edgeIn[t + 1, node]) <= 1 for t in range(0, tripNum - 1) for node in nodeList[t]),
    #              name='arrivalConstr')
    #
    # m.addConstrs((quicksum(edgeOut[t + 1, node]) <= 1 for t in range(0, tripNum - 1) for node in nodeList[t]),
    #              name='departureConstr')
    #
    m.addConstrs((quicksum(edgeOut[t + 1, eachNode]) - quicksum(edgeIn[t + 1, eachNode]) == 0 for t in range(0, tripNum - 1) for eachNode in mainNodesList[t]), name='flowConstr')


    # m.addConstrs((quicksum(edgeIn[t + 1, 'dest' + str(t + 1)]) - quicksum(edgeOut[t + 1, 'dest' + str(t + 1)]) == 1 for t in range(0, tripNum - 1)),
    #     name='destConst')

    for t in range(0, tripNum - 1):
        nodes = nodeList[t]
        m.addConstrs((quicksum(edgeIn[t + 1, node]) <= 1 for node in nodes), name='arrivalConstr')
        m.addConstrs((quicksum(edgeOut[t + 1, node]) <= 1 for node in nodes), name='departureConstr')

        mainNodes = mainNodesList[t]
        m.addConstrs((quicksum(edgeOut[t + 1, eachNode]) - quicksum(edgeIn[t + 1, eachNode]) == 0 for eachNode in mainNodes), name='flowConstr')

    # m.addConstr(quicksum(edgeOut[t + 1, 'orig' + str(t + 1)]) - quicksum(edgeIn[t + 1, 'orig' + str(t + 1)]) == 1,
    #             name='originConst')
    # m.addConstr(quicksum(edgeIn[t + 1, 'dest' + str(t + 1)]) - quicksum(edgeOut[t + 1, 'dest' + str(t + 1)]) == 1,
    #             name='destConst')

    # OverUsage Constraint for E Scooter - should include sum over all trips in a week

    m.addConstr(quicksum(
        r[edgeAttr] * eScooterTime[edgeAttr] for edgeAttr in scootEdgeAttrs.keys()) <= eScooterLimit + WeeklyOverUsage)

    obj = quicksum(tripObj) + EScooterCost * WeeklyOverUsage + WeeklyPackageCost

    #obj = quicksum(tripObj) + WeeklyPackageCost

    # set Objective
    m.setObjective(obj, GRB.MINIMIZE)
    m.optimize()
    var_values = {}
    for v in m.getVars():
        var_values[(str.encode(v.varName))] = v.x

    print("var_values are  ", var_values.items())

    with open('OptimumRouteWeek_' + str(week[-1:]) + '.csv', 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["variables", "values"])
        for key, value in var_values.items():
            writer.writerow([key, value])
