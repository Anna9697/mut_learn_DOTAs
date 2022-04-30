import json
files = ["6_2_10", "6_2_20", "6_2_30", "6_4_10", "6_6_10", "10_2_10", "case"]
for file in files:
    for i in range(3):
        items = []
        for j in range(15):
            # file_name = 'mutation-new'
            # file_name = 'generation_A&T'
            # file_name = 'generation_random'
            file_name = 'heuristic_random_testing'
            # file_name = 'selection_greedy'
            # file_name = 'operator_timed'
            # file_name = 'operator_split'
            # file_name = 'mutant_checking'
            file_path = './smart_teacher/' + file_name + '/benchmarks/' + file + '/' + file + '-' + str(1 + i) + '/' + str(1 + j) + '/result.json'
            with open(file_path, 'r') as json_model:
                model = json.load(json_model)
            # items.append(model["testNumCache"])
            # items.append(model["actionNum"])
            # items.append(model["totalTime"])
            # items.append(model["passingRate"])
            if model["correct"]:
                items.append(1)
        # print(min(items))
        # print(sum(items) / 15)
        # print(max(items))

        print(len(items))