#!/usr/bin/env python3
import json, os, math, optparse, requests, re, time, ConsoleTable
from ConsoleTable import ConsoleTable as cTable, ConsoleTableColumn as cColumn
from os.path import exists
from datetime import datetime

SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400
JSON_FILE_PATH = f"{os.path.expanduser('~')}/.animelog"

class Anime:
    STATUS_PENDING = 'Pending'
    STATUS_AIRING = 'Airing'
    STATUS_COMPLETED = 'Completed'
    modified = False

    def __init__(self, data: dict) -> None:
        self.id = data['id'] if 'id' in data.keys() else -1
        self.name = data['name'] if 'name' in data.keys() else ''
        self.alternative_titles = data['alternative_titles'] if 'alternative_titles' in data.keys() else {}
        self.episodes = data['episodes'] if 'episodes' in data.keys() else 0
        self.downloaded = data['downloaded'] if 'downloaded' in data.keys() else 0
        self.folder = data['folder'] if 'folder' in data.keys() else ''
        self.auto = data['auto'] if 'auto' in data.keys() else False
        self.alt_title = data['alt_title'] if 'alt_title' in data.keys() else ''

        if len(self.folder) > 0 and exists(self.folder) and self.auto:
            count = len([name for name in os.listdir(self.folder) if os.path.isfile(f"{self.folder}/{name}")])
            if count != self.downloaded:
                self.downloaded = count
                self.modified = True

        self.start_date = 0
        if 'start_date' in data.keys():
            if type(data['start_date']) is str:
                self.start_date = to_utc(datetime.strptime(f'{data["start_date"]} {data["start_time"]}', "%Y-%m-%d %H:%M").timestamp(), TZ_JST) if 'start_date' in data.keys() and 'start_time' in data.keys() else 0
            elif type(data['start_date']) is float:
                self.start_date = data['start_date']

        if verbose:
            print(f'Anime object instantiated: {self.to_dict()}')

        self.released = self.get_released()
        self.next_episode = self.get_next_date()
        self.status = self.get_status()

    def to_dict(self) -> dict:
        out = {}
        for attr, val in self.__dict__.items():
            out[attr] = val
        return out
    
    def get_display_title(self) -> str:
        return self.alternative_titles[self.alt_title] if self.alt_title != "" and self.alt_title in self.alternative_titles.keys() else self.name

    def get_next_date(self) -> float:
        # Start the timestamp at the time of the first episode.
        nextstamp = self.start_date

        # If the anime is finished airing then get the day of the
        # last episode by multiplying weeks and episodes.
        if self.released == self.episodes and self.episodes > 0:
            return nextstamp + (self.episodes * (SECONDS_IN_DAY * 7))

        # Loop until the given timestamp is in the future.
        while nextstamp < datetime.now().timestamp():
            nextstamp += SECONDS_IN_DAY * 7

        return nextstamp

    def get_released(self) -> int:
        if self.start_date == 0:
            return 0
        
        # Get the days since the first episode
        elapsed = datetime.now().timestamp() - self.start_date

        # Create a variable for the number of episodes released.
        released = math.ceil(elapsed/(SECONDS_IN_DAY * 7))
        if released >= self.episodes:
            released = self.episodes
        elif elapsed < 0:
            released = 0
        return released

    def get_status(self) -> str:
        released = self.get_released()
        status = self.STATUS_AIRING

        if released >= self.episodes:
            status = self.STATUS_COMPLETED
        elif released == 0:
            status = self.STATUS_PENDING
        return status

    def refresh(self) -> None:
        self.next_episode = self.get_next_date()
        self.released = self.get_released()
        self.status = self.get_status()
            
# Table widths
TABLE_WIDTH_ID = 10
TABLE_WIDTH_NAME = 40
TABLE_WIDTH_DR = 10
TABLE_WIDTH_TOTAL = 10
TABLE_WIDTH_STATUS = 10
TABLE_WIDTH_NEXT = 20

TZ_JST = 9
TZ_PST = -8
TZ_MST = -7
TZ_CST = -6
TZ_EST = -5

verbose = False
def to_utc(stamp: float, tz: int, daylight_savings=False) -> float:
    return stamp - ((tz + daylight_savings) * SECONDS_IN_HOUR)

def from_utc(stamp: float, tz: int, daylight_savings=False) -> float:
    return stamp + ((tz + daylight_savings) * SECONDS_IN_HOUR)

def load_json(file: str):
    if verbose:
        print(f'Loading {file}  data.')
    # If the file exists, load the existing json data
    if exists(file):
        f = open(file)
        data = f.read()
        # If data is found in the file then return it
        if len(data) > 0:
            return json.loads(data)
    
    print(f'Failed to load {file}. Loading empty configuration')
    # As a last resort, return blank json data.
    return {"anime": [], "autoclean": False, "apikey": None, "timezone": TZ_CST}

def save_json(data: dict, path: str):
    if verbose:
        print(f'Saving data...')

    with open(path, 'w') as out:
        out.write(f'{json.dumps(data)}\n')
        print(f"Wrote {len(str(data).encode('utf-8'))} bytes to file.")

def get_anime_index(data: dict, id: int, silent: int = False) -> int:
    # Iterate until the anime is found by id
    i=0
    for i in range(0,len(data['anime'])):
        if data['anime'][i]['id'] == id:
            if verbose:
                print(f'Found anime at index {i}.')
            return i

    # If not found return -1
    if not silent:
        print(f'Failed to locate anime by name or index')
    return -1

def add_anime(data: dict, id: int):
    anime = api_lookup(data['apikey'], id)
    
    inpt = ''
    # Get confirmation that the correct anime was found.
    while inpt.lower() != 'y' and inpt.lower() != 'n':
        # Print the anime title
        print(f'Results:') #\nID: \033[32m{anime.id}\033[0m\nTitle: \033[032m{anime.name}\033[0m')
        details(anime, color='\033[32m', timezone=data['timezone'])
        inpt = input('Is this the correct show(y/n)? ')

    if inpt.lower() == 'n':
        print('Aborting.')
        return

    if anime == None:
        print(f'Unable to find {id}')
        return
    
    if verbose:
        print(f'Checking if anime "{anime.name}" is duplicate.')
    # Verify that the anime doesn't already exist
    i = 0
    for test in data['anime']:
        if test["id"] == anime.id:
            print("This anime is already in the system.")
            return
    
    if verbose:
        print(f'Registering new anime: {anime.name}')

    data["anime"].append(anime.to_dict())

    save_json(data, JSON_FILE_PATH)
    list_anime(data)

def remove_anime(data: dict, id: int):
    if verbose:
        print(f'Getting index.')

    # Get and/or validate index
    index = get_anime_index(data, id)
    if index == -1:
        return

    # Grab the anime name for output
    anime = Anime(data['anime'][index])

    inpt = ''
    while inpt.lower() != 'y' and inpt.lower() != 'n':
        inpt = input(f'Are you sure you wish to remove {anime.name}(y/n)? ')

    if inpt.lower() == 'n':
        print('Aborted.')
        return
    
    # Remove the anime
    data['anime'].pop(index)

    # Tell the user about the removal
    print(f'Successfully removed {anime.name}.')
    save_json(data, JSON_FILE_PATH)
    list_anime(data) 

def update_anime(data: dict, id: int, update: str):
    if verbose:
        print(f'Getting index.')

    # Find the index of the given anime
    index = get_anime_index(data, id)

    if index == -1:
        return

    anime = Anime(data['anime'][index])


    # Check each variable to see if it has changed and is not the default value.
    # Default values indicate that the value was not given.
    l = []
    instructions = update.split(',')
    for instruction in instructions:
        keyval = instruction.split('=')
        if len(keyval) != 2:
            continue

        if hasattr(anime, keyval[0]):
            l.append(f'{keyval[0]}: \033[31m{getattr(anime, keyval[0])}\033[0m -> \033[32m{keyval[1]}\033[0m')
            setattr(anime, keyval[0], parse_string_value(keyval[1]))

    # If a change was actually made then save the data
    if len(l) > 0:
        inpt = ''
        while inpt.lower() != 'y' and inpt.lower() != 'n':
            print(f'Changes to be made to \033[32m{data["anime"][index]["name"]}\033[0m:')
            for line in l:
                print(f'  {line}')
            inpt = input(f'Continue? (y/n)? ')

        if inpt.lower() == 'n':
            print('Aborted.')
            return

        data['anime'][index] = anime.to_dict()
        save_json(data, JSON_FILE_PATH)

        list_anime(data)
    else:
        print("No changes detected.")

# This function has two loops in it when only one is truly necessary.
# This is done intentionally for verbose logging purposes. By instantiating
# all of the anime objects ahead of time, it is possible to alert the user to
# each change (while verbose) without it interrupting the appearance of the table
def list_anime(data: dict):
    table = cTable()
    table.add_column(cColumn(header='id', width=TABLE_WIDTH_ID, justify=ConsoleTable.JUSTIFY_RIGHT))
    table.add_column(cColumn(header='Name', width=TABLE_WIDTH_NAME))
    table.add_column(cColumn(header='D/R', width=TABLE_WIDTH_DR))
    table.add_column(cColumn(header='Total', width=TABLE_WIDTH_TOTAL))
    table.add_column(cColumn(header='Status', width=TABLE_WIDTH_STATUS))
    table.add_column(cColumn(header='Fin/Next', width=TABLE_WIDTH_NEXT))

    i = 0
    changed = False

    # Get all of the anime class objects.
    anime_list = []
    for i in range(0, len(data['anime'])):
        a = Anime(data['anime'][i])

        # If the anime object was modified at instantiation
        # (i.e. auto-updating) then flag the data to be saved.
        if a.modified:
            if verbose:
                print(f'Detected change in anime {a.id}.')
            changed = True
            data['anime'][i] = a.to_dict()

        anime_list.append(a)
    
    # If there were any changes to any anime objects then
    # save the json file with the new data.
    if changed:
        save_json(data, JSON_FILE_PATH)

    for anime in anime_list:
        # Red if there are unacquired episodes else green
        color = '\033[31m' if anime.released > anime.downloaded and anime.released > 0 else'\033[32m'

        # Create the string for the next episode date
        nxt_str = datetime.fromtimestamp(from_utc(anime.next_episode, data['timezone'], time.localtime(datetime.now().timestamp()).tm_isdst)).strftime('%Y-%m-%d %H:%M')
        table.add_row((anime.id, anime.get_display_title(), f'{anime.downloaded}/{anime.released}', anime.episodes, anime.status, nxt_str), color)
        
    table.print()

def print_anime(data: dict, id: int):
    index = get_anime_index(data, id, silent=True)
    if index == -1:
        anime = api_lookup(data['apikey'], id)
        if anime:
            details(anime=api_lookup(data['apikey'], id), color='\033[32m', timezone=data['timezone'])
        else:
            print(f'Unable to retrieve anime data for anime with id {id}. Please verify that you entered the correct id and try again.')
        return

    anime = Anime(data['anime'][index])
    if anime:
        details(anime, color='\033[32m', show_settings=True, managed=True, timezone=data['timezone'])

def clean_list(data: dict):
    print('Cleaning list.')

    # Start an indexer
    i = 0

    removed=0
    # Loop until break
    print('Searching...')
    while True:

        # Get the next anime
        anime = Anime(data['anime'][i])


        # If the next anime is complete, remove it from the list
        if anime.downloaded == anime.episodes:
            print(f' - {anime.name}')
            data['anime'].pop(i)
            removed += 1

        # If the anime is not complete then move on to the next.
        else:
            i+= 1

        # Verify that i is still within index range
        if i >= len(data['anime']):
            break

    if not removed:
        print(f'Database already clean.')
        return
    
    inpt = ''
    while not re.search('^[yn]$', inpt.lower()): #inpt.lower() != 'y' and inpt.lower() != 'n':
        inpt = input('Remove these anime?(y/n) > ')

    if inpt.lower() == 'n':
        print('Aborted')
        return
    
    print(f'Removed {removed} entries')
    save_json(data)
    list_anime(data)

def parse_string_value(s: str):
    # null/none
    if s.lower() == 'none' or s.lower() == 'null':
        if verbose:
            print(f'Parsed null value.')
        return None
        
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

def set_options(data: dict, setopt: dict):
    for key in setopt.keys():
        if verbose:
            print(f'Setting option {key} to -> {setopt[key]}')
        data[key] = setopt[key]
    
    save_json(data)

def details(anime: Anime, color='\033[0m', show_settings=False, managed=False, timezone=0):
    print(f'Found {"local" if managed else "remote"} data.')
    print(f'ID: {color}{anime.id}\033[0m')
    print(f'Title: {color}{anime.name}\033[0m')
    print(f'Alternative Titles: {color}{", ".join(map(str, anime.alternative_titles.values()))}\033[0m')
    print(f'Episodes: {color}{anime.episodes}\033[0m')

    dt = datetime.fromtimestamp(from_utc(anime.start_date, timezone, time.localtime(datetime.now().timestamp()).tm_isdst))
    print(f'Start Date: {color}{dt.date()}\033[0m')
    print(f'Start Time: {color}{dt.strftime("%H:%M")}\033[0m')

    if show_settings:
        print(f'Downloaded: {color}{anime.downloaded}\033[0m')
        print(f'Folder: {color}{anime.folder}\033[0m')
        print(f'Auto Update: {color}{True if anime.auto else False}\033[0m')

### API CODE FOR MYANIMELIST
MYANIMELIST_API_URL = 'https://api.myanimelist.net/v2'
MYANIMELIST_API_SEARCH_QUERY = 'fields=id,title,alternative_titles,start_date,status,num_episodes,broadcast'
def api_search(key: str, name: str):
    if verbose:
        print(f'Searching for {name}.')
    try:
        # Get the anime data.
        r = requests.get(f'{MYANIMELIST_API_URL}/anime?q={name}', headers={'X-MAL-CLIENT-ID': key})

        print(f'Found {len(r.json()["data"])} results')
        for node in r.json()['data']:
            print(f'{fit_str(str(node["node"]["id"]), 10, "r")}| {fit_str(node["node"]["title"], 50)}')
    except:
        print(f'Exception while attempting to search for anime.')

def api_lookup(key: str, id: int) -> Anime:
    if verbose:
        print(f'Searching for anime: {str(id)}')

    try:
        # Get the api response for the search data.
        r = requests.get(f'{MYANIMELIST_API_URL}/anime/{str(id)}?{MYANIMELIST_API_SEARCH_QUERY}', headers={'X-MAL-CLIENT-ID': key})

        if verbose:
            print(f'Response code: {r.status_code}')

        # If a valid response is received
        if r.status_code == 200:

            # Get the data
            data = r.json()

            if verbose:
                print(f'Received data:\n\n{data}\n')

            # Conver the data to an Anime object
            a = Anime({
                'id': id,
                'name': data['title'],
                'alternative_titles': {'en': data['alternative_titles']['en'], 'ja': data['alternative_titles']['ja']} if 'alternative_titles' in data.keys() else [],
                'episodes': data['num_episodes'] if 'num_episodes' in data.keys() else 0,
                'start_date': data['start_date'] if 'start_date' in data.keys() else 0,
                'start_time': data['broadcast']['start_time'] if 'broadcast' in data.keys() and 'start_time' in data['broadcast'].keys() else '00:00'
            })

            if verbose:
                print(f'Extracted data: {a.to_dict()}')

            # Return the anime object.
            return a
        else:
            print(f'Received a bad response from server.')
    except:
        print(f'Exception while attempting to lookup anime.')

def api_sync(data: dict, id: int):
    # Get the anime
    index = get_anime_index(data, id)
    if index == -1:
        return

    # Get the old data.
    old = Anime(data['anime'][index])

    # Get the new data
    new = api_lookup(data['apikey'], id)

    # l will hold a list of attribute changes to be shown.
    l = []    
    for attr in ('name', 'alternative_titles', 'episodes'):
        if getattr(old, attr) != getattr(new, attr):
            l.append(f'  {attr}: \033[31m{getattr(old, attr)}\033[0m -> \033[32m{getattr(new, attr)}\033[0m')
            setattr(old, attr, getattr(new, attr))

    # If there are no changes then output to user and exit.
    if len(l) == 0:
        print('No changes found.')
        return
    
    # Describe the changes to the user.
    print('Changes:')
    for c in l:
        print(c)

    # Get confirmation before making changes.
    inpt = ''
    while not re.search('^[yn]$', inpt):
        inpt = input('Proceed? (y/n) > ')

    # If the user declined the changes abort
    if inpt.lower() == 'n':
        print('Aborting.')
        return

    data['anime'][index] = old.to_dict()
    save_json(data, JSON_FILE_PATH)

### COMMAND EXECUTION CODE
def execute(options: optparse.OptionParser):
    (options, args) = parser.parse_args()

    # Set verbose logging state.
    global verbose
    verbose = options.verbose
    if verbose:
        print(f'Verbose logging enabled.')
    
    # Default to listing if no arguments provided.
    if len(args) == 0 or args[0].lower() == 'list':
        list_anime(load_json(JSON_FILE_PATH))

    # Printing details of an anime.
    elif args[0].lower() == 'details':
        if len(args) < 2: # Too few args
            print('Unable to search: Missing name.')
        elif len(args) > 2:# Too many args
            print('Unable to search: Too many arguments.')
        else:
            print_anime(load_json(JSON_FILE_PATH), int(args[1]))

    # Searching MyAnimeList.net for an anime.
    elif args[0].lower() == 'search':
        if len(args) < 2: # Too few args
            print('Unable to search: Missing name.')
        elif len(args) > 2:# Too many args
            print('Unable to search: Too many arguments.')
        else:
            api_search(load_json(JSON_FILE_PATH)['apikey'], args[1])

    # Adding an anime to the system.
    elif args[0].lower() == 'add':
        if len(args) < 2: # Too few args
            print('Unable to add: Missing ID')
        elif len(args) > 2: # Too many args
            print('Unable to add: Too many arguments')
        elif not args[1].isnumeric():
            print('Unable to add: id must be numeric.')
        else:
            add_anime(load_json(JSON_FILE_PATH), int(args[1]))

    # Removing an anime from the system.
    elif args[0].lower() == 'remove':
        if len(args) < 2: # Too few args
            print('Unable to remove: Missing ID')
        elif len(args) > 2: # Too many args
            print('Unable to remove: Too many arguments')
        elif not args[1].isnumeric():
            print('Unable to add: id must be numeric.')
        else:
            remove_anime(load_json(JSON_FILE_PATH), int(args[1]))
            pass

    # Updating an anime in the system.
    elif args[0].lower() == 'update':
        if len(args) == 1: # Too few args
            print('Unable to update: Missing ID')
        if len(args) < 3: # Too few args
            print('Unable to update: Missing update string.')
        elif len(args) > 3: # Too many args
            print('Unable to update: Too many arguments')
        elif not args[1].isnumeric():
            print('Unable to add: id must be numeric.')
        else:
            update_anime(load_json(JSON_FILE_PATH), int(args[1]), args[2])
    
    # Sync anime information from MyAnimeList.net
    elif args[0].lower() == 'sync':
        if len(args) < 2: # Too few args
            print('Unable to sync: Missing ID')
        elif len(args) > 2: # Too many args
            print('Unable to sync: Too many arguments')
        elif not args[1].isnumeric():
            print('Unable to sync: id must be numeric.')
        else:
            api_sync(load_json(JSON_FILE_PATH), int(args[1]))

    # Remove any anime that are finished.
    elif args[0].lower() == 'clean':
        clean_list(load_json(JSON_FILE_PATH))

    # Set program options.
    elif args[0].lower() == 'setopt':
        set_options(options.setopt)
    
    else:
        print(f'Unknown action: {args[0]}\nPlease retry or use the -h flag for help.')

#json_data = load_json()
if __name__ == "__main__":
    parser = optparse.OptionParser(
"""usage: animemgr.py [action] [args] [options]
Actions:
  list:    (list)            Lists all tracked anime.
  details: (details [id] [option])
                             Get the details of an anime. Options:
                               local -  Only attempts to get local anime data.
                                        If local data is unavailable for the given
                                        id then the details will fail to print
                                remote- Only attempts to get remote anime data
                                        from MyAnimeList api.
  search:  (search [name])   Searches for anime by name.
  add:     (add [id])        Add anime by id.
  remove:  (remove [id])     Remove anime by id.
  update:  (update [id])     Update given anime data.
  sync:    (sync [id])       Redownloads data for given id. if no id given
                             syncs all tracked anime.
  clean:   (clean)           Removes all completed and saved anime.
  setopt   (setopt opt1=val,opt2=val)
                             Sets the options in the given string to the
                             provided values."""
    )

    parser.add_option('-a', '--acquired', dest='downloaded', default=-1, type='int', help='number of episodes already acquired.')
    parser.add_option('-i', '--id', dest='id', default='', type='string', help='the index of the listed anime.')
    parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true', help='Enables verbose logging.')

    execute(parser)
