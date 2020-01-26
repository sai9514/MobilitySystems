import geopy.distance
from gurobipy import *
import networkx as nx
import csv
from MobilitySystems import getData
import matplotlib.pyplot as plt

# getting weekly user trips
user_weekly_trips = getData.getUserWeeklyTripDetails()
valueTime = 0.00322222222
ulEscoot = 1
eScooterLimit = 1200
EScooterCost = 0.003
WeeklyPackageCost = 34


for week in user_weekly_trips:
    trips = user_weekly_trips[week]  # includes all the trips for this week as an array
    m = Model('WeeklyPackageRoutes')
    WeeklyOverUsage = m.addVar(vtype=GRB.INTEGER, name='WeeklyOverUsage')
    r = {}
    edgeAttrs = {}
    publicEdgeAttrs = {}
    scootEdgeAttrs = {}
    edgeIn = {}
    edgeOut = {}
    subNodesList = []
    monValTime = {}
    eScooterTime = {}
    eScooterUnlockCost = {}
    tripNum = 0
    # print(week)
    for trip in trips:
        orig = trip[0]
        dest = trip[1]

        # getting the network file with public transport and e scooters
        G = nx.read_gpickle("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/networkBerlin1.gpickle")
        # nx.draw_networkx(G, with_labels=True, node_size=10, font_size=2, arrowsize=4)
        # plt.savefig("/home/sai/PycharmProjects/BerlinRoutes/OutputGraphs/sample_" + str(week) + "_" + str(tripNum) + ".pdf", bbox_inches='tight', format='pdf', dpi=1200)

        node_attrs = nx.get_node_attributes(G, name='locale')
        print(*node_attrs)
        print("No. of initial edges ", nx.number_of_edges(G))

        # adding links between orig or dest to stops or e scooters

        for item in node_attrs.items():
            d1 = geopy.distance.vincenty(orig, item[1]).km
            d2 = geopy.distance.vincenty(dest, item[1]).km
            if "es_" not in item[0]:  # for public transport stops
                if d1 < 4:
                    G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
                if d2 < 4:
                    G.add_edge(item[0], "dest", key='walk', attrs={"walk": int(720 * d2)})
            else:  # for e scooter stops
                if d1 < 4:
                    G.add_edge("orig", item[0], key='walk', attrs={"walk": int(720 * d1)})
                if d2 < 5:
                    G.add_edge(item[0], "dest", key='scoot', attrs={"scoot": int(180 * d2)})
        print("No. of edges after orig, dest and e scooters: ", nx.number_of_edges(G))
        edgeList = G.edges.data('attrs')
        for eachEdge in edgeList:
            edgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
            if 'walk' not in eachEdge[2].keys():
                if 'scoot' not in eachEdge[2].keys():
                    publicEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
                else:
                    scootEdgeAttrs[tripNum, (eachEdge[0], eachEdge[1])] = eachEdge[2]
        for edges in edgeAttrs:
            if edges[0] == tripNum:
                edgeLink = (edges[1][0], edges[1][1])
                u = edges[1][0]
                v = edges[1][1]
                r[tripNum, edgeLink] = m.addVar(vtype=GRB.BINARY, name='route_' + str(tripNum) + str(edgeLink))
                if (tripNum, v) in edgeIn:
                    edgeIn[tripNum, v].append(r[tripNum, edgeLink])
                else:
                    edgeIn[tripNum, v] = [r[tripNum, edgeLink]]
                if (tripNum, u) in edgeOut:
                    edgeOut[tripNum, u].append(r[tripNum, edgeLink])
                else:
                    edgeOut[tripNum, u] = [r[tripNum, edgeLink]]

        subNodesList.append(list(G.nodes()))

        # write the timings in csv file for viewing
        with open('/home/sai/PycharmProjects/BerlinRoutes/OutputsGurobi/' + week + '_timings_trip_' + str(tripNum) + '.csv', 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["edges", "timings"])
            for edgeAttr in edgeAttrs:
                if edgeAttr[0] == tripNum:
                    writer.writerow([str.encode(str(edgeAttr[1])), int(list(edgeAttrs[edgeAttr].values())[0])])
        plt.clf()
        tripNum += 1

    for nodes in subNodesList:
        nodes.remove('orig')
        nodes.remove('dest')
        print(*nodes)

    for edgeAttr in edgeAttrs:
        monValTime[edgeAttr[0], edgeAttr[1]] = int(list(edgeAttrs[edgeAttr].values())[0]) * valueTime

    for edgeAttr in scootEdgeAttrs:
        eScooterTime[edgeAttr[0], edgeAttr[1]] = (int(list(edgeAttrs[edgeAttr].values())[0]))
        eScooterUnlockCost[edgeAttr[0], edgeAttr[1]] = ulEscoot

    # constraint to make sure each node is left if it is reached (flow constraint)
    for t in range(0, tripNum):
        # origin constraint
        m.addConstr((quicksum(edgeOut[t, 'orig']) == 1), name='originConst')

        # destination constraint
        m.addConstr((quicksum(edgeIn[t, 'dest']) == 1), name='destConst')

        for node in subNodesList[t]:
            # node = subNodes[i]
            # constraint to make sure each node is left if it is reached (flow constraint)
            m.addConstr(quicksum(edgeOut[t, node]) - quicksum(edgeIn[t, node]) == 0, name='flowConstr')

            # constraint to make sure only one edge reaches a node
            m.addConstr(quicksum(edgeIn[t, node]) <= 1, name='arrivalConstr')

            # constraint to make sure only one edge is leaving a node
            m.addConstr(quicksum(edgeOut[t, node]) <= 1, name='departConstr')

    # Weekly OverUsage Constraint
    m.addConstr(quicksum(r[edgeAttr] * eScooterTime[edgeAttr] for edgeAttr in scootEdgeAttrs.keys()) <= eScooterLimit + WeeklyOverUsage)

    # Objective Function
    obj = quicksum(r[edgeAttr] * monValTime[edgeAttr] for edgeAttr in edgeAttrs.keys()) + \
          quicksum(r[edgeAttr] * (eScooterUnlockCost[edgeAttr]) for edgeAttr in scootEdgeAttrs.keys()) + \
          EScooterCost * WeeklyOverUsage + WeeklyPackageCost

    m.setObjective(obj, GRB.MINIMIZE)
    m.optimize()
    var_values = {}
    for v in m.getVars():
        var_values[(str.encode(v.varName))] = v.x

    print("var_values are  ", var_values.items())

    with open('/home/sai/PycharmProjects/BerlinRoutes/OutputsGurobi/' +'OptimumRouteWeek_' + str(week[-1:]) + '.csv', 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["variables", "values"])
        for key, value in var_values.items():
            if value != 0:
                writer.writerow([key, value])
