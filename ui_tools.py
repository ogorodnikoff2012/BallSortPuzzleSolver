def select_from_list(lst):
    selection_index = None
    while selection_index is None:
        print("Choose one of the following options:")
        for i, element in enumerate(lst):
            print(f"{i+1}:\t{element}")

        answer = input("Enter option index (default=1): ")
        if len(answer) == 0:
            selection_index = 0
            break

        if not answer.isdigit():
            continue

        value = int(answer) - 1

        if value < 0 or value >= len(lst):
            continue

        selection_index = value

    return selection_index


def msg(*args, sep=None):
    print(*args, sep=sep)
