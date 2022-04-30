import copy
import smart_learning.obsTable as obsTable
from common.hypothesis import struct_discreteOTA, struct_hypothesisOTA
from smart_learning.teacher import EQs


def learnOTA_smart(system, debug_flag, exp, generate, selection, operator):
    actions = system.actions

    ### init Table
    table = obsTable.initTable(actions, system)
    if debug_flag:
        print("***************** init-Table_1 is as follow *******************")
        table.show()

    ### learning start
    equivalent = False
    learned_system = None  # learned model
    table_num = 1  # number of table
    ctx = []

    while not equivalent:
        ### make table prepared
        prepared = table.is_prepared()
        while not prepared:
            # make closed
            closed_flag, close_move = table.is_closed()
            if not closed_flag:
                table = obsTable.make_closed(table, actions, close_move, system)
                table_num = table_num + 1
                if debug_flag:
                    print("***************** closed-Table_" + str(table_num) + " is as follow *******************")
                    table.show()

            # make consistent
            consistent_flag, consistent_add = table.is_consistent()
            if not consistent_flag:
                consistent_flag, consistent_add = table.is_consistent()
                table = obsTable.make_consistent(table, consistent_add, system)
                table_num = table_num + 1
                if debug_flag:
                    print("***************** consistent-Table_" + str(table_num) + " is as follow *******************")
                    table.show()
            prepared = table.is_prepared()

        ### build hypothesis
        # Discrete OTA
        discreteOTA = struct_discreteOTA(table, actions)
        if discreteOTA is None:
            raise Exception('Attention!!!')
        if debug_flag:
            print("***************** discreteOTA_" + str(system.eq_num + 1) + " is as follow. *******************")
            discreteOTA.show_discreteOTA()
        # Hypothesis OTA
        hypothesisOTA = struct_hypothesisOTA(discreteOTA)
        if debug_flag:
            print("***************** Hypothesis_" + str(system.eq_num + 1) + " is as follow. *******************")
            hypothesisOTA.show_OTA()

        ### EQs
        equivalent, ctx = EQs(hypothesisOTA, system, ctx, exp, generate, selection, operator)

        if not equivalent:
            # show ctx
            if debug_flag:
                print("***************** counterexample is as follow. *******************")
                print([dtw.show() for dtw in ctx])
            print("***************** counterexample is as follow. *******************")
            print([dtw.show() for dtw in ctx])
            # deal with ctx
            table = obsTable.deal_ctx(table, ctx, system)
            table_num = table_num + 1
            if debug_flag:
                print("***************** New-Table" + str(table_num) + " is as follow *******************")
                table.show()
        else:
            learned_system = copy.deepcopy(hypothesisOTA)

    return learned_system, system.mq_num, system.eq_num, system.test_num, system.test_num_cache, system.action_num, system.total_time, table_num
