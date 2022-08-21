#!/usr/bin/env python3
import json, os, math, optparse, requests
from os.path import exists
from datetime import datetime

SECONDS_IN_DAY = 86400
JSON_FILE_PATH = f"{os.path.expanduser('~')}/.animelog"

# Table widths
TABLE_WIDTH_ID = 6
TABLE_WIDTH_NAME = 40
TABLE_WIDTH_DR = 10
TABLE_WIDTH_TOTAL = 5
TABLE_WIDTH_STATUS = 10

verbose = False

def load_json():
    if verbose:
        print(f'Loading {JSON_FILE_PATH}  data.')
    # If the file exists, load the existing json data
    if exists(JSON_FILE_PATH):
        f = open(JSON_FILE_PATH)
        data = f.read()
        # If data is found in the file then return it
        if len(data) > 0:
            return json.loads(data)
    
    print(f'Failed to load {JSON_FILE_PATH}. Loading empty configuration')
    # As a last resort, return blank json data.
    return {"anime": [], "autoclean": False}

def save_json():
    if verbose:
        print(f'Saving data...')

    with open(JSON_FILE_PATH, 'w') as out:
        out.write(json.dumps(json_data))
        print(f"Wrote {len(str(json_data).encode('utf-8'))} bytes to file.")

def fit_str(s:str, length: int, justify: str = 'l') -> str:
    spaces = length - len(s)
    if spaces > 0:
        sp = ' ' * spaces

        if justify == 'r':
            return sp+s
        elif justify == 'c':
            sp = ' ' * (math.floor(spaces / 2))
            ssp = ' ' * (math.ceil(spaces / 2))

            return sp+s+ssp
        else:
            return s+sp

    elif spaces < 0:
        return s[0:length]
    else:
        return s

def get_schedule_rotation(schedule:str ):
    if schedule == 'weekly':
        return SECONDS_IN_DAY * 7
    elif schedule == 'biweekly':
        return SECONDS_IN_DAY * 14
    elif schedule == 'monthly':
        return SECONDS_IN_DAY * 28
    elif schedule == 'bimonthly':
        return SECONDS_IN_DAY * 56
    else:
        return -1

def calc_next_date(stamp: float, schedule: str):
    rotation = get_schedule_rotation(schedule)
    if rotation == -1:
        return ''

    nextstamp = stamp
    # Loop until the given timestamp is in the future.
    while nextstamp < datetime.now().timestamp():
        nextstamp += rotation

    return nextstamp

def find_anime_by_name_or_index(name: str, index: int) -> int:
    # If the index is good, return it
    if index >= 0 and index < len(json_data['anime']):
        return index

    # Iterate until the anime is found and return index
    i = 0
    for i in range(0,len(json_data['anime'])):
        if json_data['anime'][i]['name'] == name:
            return i

    # If not found return -1
    print(f'Failed to locate anime by name or index')
    return -1

def register_anime(name: str, schedule: str, firstepisodedate: str, episodes, downloaded):
    if verbose:
        print(f'Checking if anime "{name}" is duplicate.')
    # Verify that the anime doesn't already exist
    i = 0
    for anime in json_data['anime']:
        if anime["name"].lower() == name.lower():
            print("This anime is already in the system.")
            return
    
    if verbose:
        print(f'Registering new anime: {name}')

    # Set default values where required
    if schedule == '':
        if verbose:
            print(f'Using default schedule: weekly')
        schedule = 'weekly'
    if firstepisodedate == '':
        if verbose:
            print(f'Using default pilot air date: 01/01/1995 00:00:00')
        firstepisodedate = "01/01/1995 00:00:00"
    if episodes == -1:
        if verbose:
            print(f'Using default episodes: 12')
        episodes = 12
    if downloaded == -1:
        if verbose:
            print(f'Using default download count: 0')
        downloaded = 0

    # Create the anime object.
    dt = datetime.strptime(firstepisodedate, '%m/%d/%Y %H:%M:%S')
    
    a = {
        "name": name,
        "schedule": schedule,
        "firstepisodedate": dt.timestamp(),
        "episodes": episodes,
        "downloaded": downloaded
    }

    json_data["anime"].append(a)
    save_json()
    list_anime()

def deregister_anime(name, index):
    if verbose:
        print(f'Getting index...')

    # Get and/or validate index
    index = find_anime_by_name_or_index(name, index)
    if index == -1:
        return

    # Grab the anime name for output
    if name == '':
        name = json_data['anime'][index]['name']

    inpt = ''
    while inpt.lower() != 'y' and inpt.lower() != 'n':
        inpt = input(f'Are you sure you wish to remove {name}(y/n)? ')

    if inpt.lower() == 'n':
        print('Aborted.')
        return
    
    # Remove the anime
    json_data['anime'].remove(json_data['anime'][index])

    # Tell the user about the removal
    print(f'Successfully removed {name}.')
    save_json()
    list_anime()

def update_anime(name: str, index: int, schedule: str, firstepisodedate, episodes, downloaded):
    if verbose:
        print(f'Getting index.')

    # If index is set that makes things easier
    index = find_anime_by_name_or_index(name, index)

    if index == -1:
        return

    # Check each variable to see if it has changed and is not the default value.
    # Default values indicate that the value was not given.
    l = []
    if len(name) > 0 and name != json_data['anime'][index]['name']:
        l.append(f'name: \033[31m{json_data["anime"][index]["name"]}\033[0m -> \033[32m{name}\033[0m')
        if verbose:
            print(f'Detected change in name: \033[31m{json_data["anime"][index]["name"]}\033[0m -> \033[32m{name}\033[0m')
        json_data['anime'][index]['name'] = name

    if len(schedule) > 0 and schedule != json_data['anime'][index]['schedule']:
        l.append(f'schedule: \033[31m{json_data["anime"][index]["schedule"]}\033[0m -> \033[32m{schedule}')
        if verbose:
            print(f'Detected change in schedule: \033[31m{json_data["anime"][index]["schedule"]}\033[0m -> \033[32m{schedule}\033[0m')
        json_data['anime'][index]['schedule'] = schedule

    if len(firstepisodedate) > 0 and firstepisodedate != json_data['anime'][index]['firstepisodedate']:
        l.append(f'Orignal Air Date: \033[31m{json_data["anime"][index]["firstepisodedate"]}\033[0m -> \033[32m{firstepisodedate}\033[0m')
        if verbose:
            print(f'Detected change in pilot date: \033[31m{json_data["anime"][index]["firstepisodedate"]}\033[0m -> \033[32m{firstepisodedate}\033[0m')
        json_data['anime'][index]['firstepisodedate'] = firstepisodedate

    if episodes > 0 and episodes != json_data['anime'][index]['episodes']:
        l.append(f'episodes: \033[31m{json_data["anime"][index]["episodes"]}\033[0m -> \033[32m{episodes}\033[0m')
        if verbose:
            print(f'Detected change in episodes: \033[31m{json_data["anime"][index]["episodes"]}\033[0m -> \033[32m{episodes}\033[0m')
        json_data['anime'][index]['episodes'] = episodes
    
    if downloaded > 0 and downloaded != json_data['anime'][index]['downloaded']:
        l.append(f'downloaded: \033[31m{json_data["anime"][index]["downloaded"]}\033[0m -> \033[32m{downloaded}\033[0m')
        if verbose:
            print(f'Detected change in downloaded: \033[31m{json_data["anime"][index]["downloaded"]}\033[0m -> \033[32m{downloaded}\033[0m')
        json_data['anime'][index]['downloaded'] = downloaded

    # If a change was actually made then save the data
    if len(l) > 0:
        
        inpt = ''
        while inpt.lower() != 'y' and inpt.lower() != 'n':
            print(f'Changes to be made to \033[32m{json_data["anime"][index]["name"]}\033[0m:')
            for line in l:
                print(f'  {line}')
            inpt = input(f'Continue? (y/n)? ')

        if inpt.lower() == 'n':
            print('Aborted.')
            return
        save_json()

        list_anime()
    else:
        print("No changes detected.")

def list_anime():    
    print(f'{fit_str("id", TABLE_WIDTH_ID, "r")}| {fit_str("Name", TABLE_WIDTH_NAME)}| {fit_str("D/R", TABLE_WIDTH_DR)}| {fit_str("Total", TABLE_WIDTH_TOTAL)}| {fit_str("Status", TABLE_WIDTH_STATUS)}| Fin/Next')

    i = 0
    for i in range(0, len(json_data['anime'])):
        a = json_data['anime'][i]
        # Get the days since the first episode
        elapsed = datetime.now().timestamp() - a['firstepisodedate']

        released = 0

        if ( a['schedule'] == 'weekly' ):
            released = math.ceil(elapsed/get_schedule_rotation(a['schedule']))

        nextdate = ''
        if released >= a['episodes']:
            released = a['episodes']
            status = 'completed'
        
        elif released > 0:
            status = 'airing'
            nextdate = calc_next_date(a['firstepisodedate'], a['schedule'])

        else:
            status = 'pending'
            released = 0
        
        id_str = f'{fit_str(str(i), TABLE_WIDTH_ID, "r")}'
        name_str = f'{fit_str(a["name"], TABLE_WIDTH_NAME)}'
        dr_str = fit_str(f'{a["downloaded"]}/{released}', TABLE_WIDTH_DR)
        t_str = fit_str(str(a['episodes']), TABLE_WIDTH_TOTAL)
        status = fit_str(status, TABLE_WIDTH_STATUS)


        print('-'*(TABLE_WIDTH_ID+TABLE_WIDTH_NAME+TABLE_WIDTH_DR+TABLE_WIDTH_TOTAL+TABLE_WIDTH_STATUS+20))

        color = '\033[32m'
        if released > a['downloaded'] and released > 0:
            color = '\033[31m'
        nxt_str = ''
        if nextdate != '':
            nxt_str = f'{datetime.fromtimestamp(nextdate)}'
        else:
            nxt_str = f'{datetime.fromtimestamp(a["firstepisodedate"] + (a["episodes"]*get_schedule_rotation(a["schedule"])))}'
            
        print(f'{color}{id_str}\033[0m| {color}{name_str}\033[0m| {color}{dr_str}\033[0m| {color}{t_str}\033[0m| {color}{status}\033[0m| {color}{nxt_str}\033[0m')

def clean_list():
    print('Cleaning list.')

    # Start an indexer
    i = 0

    removed=0
    # Loop until break
    while True:

        # Get the next anime
        anime = json_data['anime'][i]

        # If the next anime is complete, remove it from the list
        if anime['downloaded'] == anime['episodes']:
            if verbose:
                print(f'Removing {anime["name"]}...')

            json_data['anime'].remove(anime)
            removed += 1

        # If the anime is not complete then move on to the next.
        else:
            i+= 1

        # Verify that i is still within index range
        if i >= len(json_data['anime']):
            break
    print(f'Removed {removed} entries')
    save_json()

def parse_string_value(s: str):
    # boolean true
    if s.lower() == 'true':
        if verbose:
            print(f'Parsed boolean value: True')
        return True
        
    # boolean false
    elif s.lower() == 'false':
        if verbose:
            print(f'Parsed boolean value: False')
        return False

    # integer
    elif s.isnumeric():
        if verbose:
            print(f'Parsed numeric value: {int(s)}')
        return int(s)

    # string
    else:
        if verbose:
            print(f'Parsed string value: {s}')
        return str(s)

def parse_list_callback(option, opt_str, value, parser) -> list:
    rtn = {"flags": json_data['flags']}
    splt = value.split(",")

    if verbose:
        print(f'Parsed setopt commands: {splt}')

    # opt_str should look like
    # opt1=True,opt2=1,opt3=false
    i = 0
    for i in range(0, len(splt)):
        kv = splt[i].split('=')

        # If given a key-value pair then process accordingly
        if len(kv) == 2:
            rtn[kv[0]] = parse_string_value(kv[1])
        
        # If not a key-value pair then simply append it.
        else:
            rtn['flags'].append(parse_string_value(splt[i]))

    parser.values.setopt = rtn

def set_options(setopt: dict):
    for key in setopt.keys():
        if verbose:
            print(f'Setting option {key} to -> {setopt[key]}')
        json_data[key] = setopt[key]
    
    save_json()

### API CODE FOR MYANIMELIST
MYANIMELIST_API_URL = 'https://api.myanimelist.net/v2'
def do_api_test():
    r = requests.get(f'{MYANIMELIST_API_URL}/anime?q=one&limit=4')
    print(r.json())

json_data = load_json()
if __name__ == "__main__":
    parser = optparse.OptionParser("usage: animemgr.py [options]")
    parser.add_option('-n', '--name', dest='name', default='', type='string', help='name of the anime.')
    parser.add_option('-s', '--schedule', dest='schedule', default='', type='string', help='episode release schedule (weekly/biweekly/montly/bimonthly)')
    parser.add_option('-d', '--date', dest='firstepisode', default='', type='string', help='the mm/dd/yyyy of first episode release.')
    parser.add_option('-e', '--episodes', dest='episodes', default=-1, type='int', help='number of episodes to be aired.')
    parser.add_option('-a', '--acquired', dest='downloaded', default=-1, type='int', help='number of episodes already acquired.')
    parser.add_option('-i', '--index', dest='index', default=-1, type='int', help='the index of the listed anime.')
    parser.add_option('--set-opt', dest='setopt', action='callback', type='string', callback=parse_list_callback, default={}, help='A list of settings to set.')
    parser.add_option('-c', '--clean', dest='clean', default=False, action='store_true', help='Removes all completed anime from the database.')
    parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true', help='Enables verbose logging.')

    parser.add_option('-l', '--list', dest='act', action='store_const', const='list', default='', help='Sets the program to list anime. (default action)')
    parser.add_option('-r', '--register', dest='act', action='store_const', const='reg', help='Sets the program to registration mode.')
    parser.add_option('-x', '--deregister', dest='act', action='store_const', const='dereg', help='Sets the program to deregistration mode.')
    parser.add_option('-u', '--update', dest='act', action='store_const', const='update', help='Update an animes information')

    parser.add_option('--beta', dest='beta', action='store_true', default=False, help='Enables api testing mode.')
    
    (options, args) = parser.parse_args()

    # Set verbose logging state.
    verbose = options.verbose
    if verbose:
        print(f'Verbose logging enabled.')

    # If options are being set then that overrides everything else
    if len(options.setopt) > 0:
        set_options(options.setopt)
        
    if options.clean:
        clean_list()
    
    if options.beta:
        do_api_test()

    # If there is no specified action
    elif options.act == '':
        idx = find_anime_by_name_or_index(options.name, options.index)
        # If a name was given and no anime by that name exists create it
        if options.name != '' and idx == -1:
            register_anime(options.name, options.schedule, options.firstepisode, options.episodes, options.downloaded)

        # if a name or index was given and the anime exists then update it if other arguments exist.
        elif idx > -1 and (options.schedule != '' or options.firstepisode != json_data['anime'][idx]['firstepisodedate'] or options.episodes != json_data['anime'][idx]['episodes'] or options.downloaded != json_data['anime'][idx]['downloaded']):
            update_anime(options.name, options.index, options.schedule, options.firstepisode, options.episodes, options.downloaded)

        else:
            list_anime()

    elif options.act == 'list':
        list_anime()

    elif options.act == 'reg':
        if options.name == '':
            parser.error("Missing required argument [name]")
        else:
            register_anime(options.name, options.schedule, options.firstepisode, options.episodes, options.downloaded)
    elif options.act == 'dereg':
        if options.name == '' and options.index == -1:
            parser.error("Missing required argument. deregistration requires either [name] or [index] to be set.")
        else:            
            deregister_anime(options.name, options.index)

    elif options.act == 'update':
        if options.name == '' and options.index == -1:
            parser.error("Missing required argument. update requires either [name] or [index] to be set.")
        else:
            update_anime(options.name, options.index, options.schedule, options.firstepisode, options.episodes, options.downloaded)
