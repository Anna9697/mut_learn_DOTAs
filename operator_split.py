# main file
import sys
import random
import json
import time
from common.system import build_system
from common.make_pic import make_system, make_hypothesis
from smart_learning.learnOTA import learnOTA_smart
from common.validate import validate

import multiprocessing


def main(params_temp):
    debug_flag = False
    path_temp = params_temp[2]
    i_temp = params_temp[0]
    j_temp = params_temp[1]

    # used to reproduce experimental results
    random.seed(j_temp)

    exp = 'mutation_new'
    generate = 'heuristic'
    selection = 'score'
    operator = 'split'
    model_file = "benchmarks/" + path_temp + "/" + path_temp + "-" + str(i_temp + 1) + ".json"
    teacher_type = "smart_teacher"
    temp_path = '/'.join(model_file.split('/')[: -1]) + '/' + model_file.split('/')[-1].split('.')[0] + "/" + str(j_temp + 1)

    result_path = 'results/' + teacher_type + '/' + 'operator_split' + '/' + temp_path

    # get model information and build target system
    with open(model_file, 'r') as json_model:
        model = json.load(json_model)
    system = build_system(model)
    make_system(system, result_path, '/model_target')

    # mutation learning of DOTAs
    start_time = time.time()
    print("********** learning starting *************")
    if teacher_type == "smart_teacher":
        learned_system, mq_num, eq_num, test_num, test_num_cache, action_num, total_time, table_num = learnOTA_smart(system, debug_flag, exp, generate, selection, operator)
    elif teacher_type == "normal_teacher":
        raise Exception('Not supported normal_teacher !')
    else:
        raise Exception('Teacher type only allows two options: smart_teacher and normal_teacher.')
    end_time = time.time()

    # learning result
    if learned_system is None:
        print("Error! Learning Failed.")
        print("*********** learning ending  *************")
        return {"result": "Failed"}
    else:
        print("———————————————————————————————————————————")
        print("Succeed! The result is as follows:")
        # validate
        make_hypothesis(learned_system, result_path, '/model_hypothesis')
        correct_flag, passing_rate = validate(learned_system, system)
        print("Total time of learning: " + str(end_time - start_time))
        print("Total number of MQs (no-cache): " + str(mq_num))
        print("Total number of EQs: " + str(eq_num))
        print("Total number of tests (no-cache): " + str(test_num))
        print("Total number of tests (with-cache): " + str(test_num_cache))
        print("Total number of actions: " + str(action_num))
        print("Total number of actions: " + str(total_time))
        print("Total number of tables explored: " + str(table_num))
        print("Completely correct: " + str(correct_flag) + "   Testing pass rate: " + str(passing_rate))
        print("*********** learning ending  *************")
        trans = []
        for t in learned_system.trans:
            trans.append([str(t.tran_id), str(t.source), str(t.action), t.show_guards(), str(t.reset), str(t.target)])
        result_obj = {
            "result": "Success",
            "learningTime": end_time - start_time,
            "mqNum": mq_num,
            "eqNum": eq_num,
            "testNum": test_num,
            "testNumCache": test_num_cache,
            "actionNum": action_num,
            "totalTime": total_time,
            "tableNum": table_num,
            "correct": correct_flag,
            "passingRate": passing_rate,
            "model": {
                "actions": learned_system.actions,
                "states": learned_system.states,
                "initState": learned_system.init_state,
                "acceptStates": learned_system.accept_states,
                "sinkState": learned_system.sink_state,
                "trans": trans
            }
        }
        with open(result_path + "/result.json", 'w') as json_file:
            json_file.write(json.dumps(result_obj, indent=2))
        return result_obj


if __name__ == '__main__':
    paths = ["case", "6_2_10", "6_2_20", "6_2_30", "6_4_10", "6_6_10", "10_2_10"]
    for path in paths:
        for i in range(3):
            pool = multiprocessing.Pool(int(multiprocessing.cpu_count() / 2))
            params = []
            for j in range(15):
                params.append((i, j, path))
            results = pool.map(main, params)
            pool.close()
            pool.join()
