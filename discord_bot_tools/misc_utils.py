import os
import re

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_valid_filename(s):
    """
    Get a valid filename given a string s, and return it.
    Courtesy of Django's open source code: https://github.com/django/django/blob/master/django/utils/text.py
    """
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def get_date_str(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")

def sort_log(log):
    key = lambda msg: (str(msg.server), str(msg.channel), str(msg.timestamp))
    log = sorted(log, key=key)
    return log

def get_msg_str(msg):
    """
    Arguments:
        msg: Discord.py Message object
    Returns:
        Gets a string formatted like
            date-author-content
        This should only be used when looking at one channel,
            since it doesn't include any server, channel, or even private message specifiers
            as for the location or origin of each message
    """
    return get_date_str(msg.timestamp) + "-" + str(msg.author) + ": " + str(msg.clean_content) + "\n"

def get_global_msg_str(msg):
    """
    Arguments:
        msg: Discord.py Message object
    Returns:
        Gets a string formatted like
            server(will not be included if private message)-channel(or private message if not a channel)-date-author-content
        This can be used when looking at any channel,
            since it includes specifiers as for the location or origin of each message
    """
    #Check if Server Message or Private Message
    msg_str = ""
    if msg.server == None:
        #Private Message / Group Message
        #Check if Private Message or Group Message
        private_channel = msg.channel
        if len(private_channel.recipients) == 1:
            #One user message / Private Message
            channel = private_channel.user.name

        else:
            #Two+ user message / Group Message
            channel = '-'.join([user.name for user in private_channel.recipients])
        msg_str += channel
    else:
        #Channel Message from Server
        server = str(msg.server)
        channel = str(msg.channel)
        msg_str += server + "-" + channel

    msg_str += "-"

    #then we simply add on the remaining content as in get_msg_str()
    msg_str += get_msg_str(msg).strip()
    return msg_str

def recursive_get_paths(directory):
    """
    Arguments:
        directory : directory to recursively traverse. Should be a string.

    Returns:
        A list of filepaths, e.g.:
            "/home/darkelement/test.txt"        
    """
    paths = []
    for (path, dirs, fnames) in os.walk(directory):
        for fname in fnames:
            paths.append(os.path.join(path, fname))
    return paths

def ensure_necessary_log_dirs(client):
    """
    Given a discord.py Client object, ensures that all directories are created for logging from any private message, channel, server, and so on.
    Will format as:
    <user>/
        servers/
            <server1>/
                <channel logfile>
                ...
            ...
        private messages/
            <logfile>
            ...
        private group messages/
            <logfile>
            ...
    """
    servers = [server for server in client.servers]
    channels = [channel for channel in client.get_all_channels()]
    private_channels = [private_channel for private_channel in client.private_channels]

    for server in servers:
        log_dir = get_valid_filename(client.user.name) + os.sep + "Servers" + os.sep + get_valid_filename(server.name)
        ensure_dir(log_dir)

    log_dir = get_valid_filename(client.user.name) + os.sep + "Private_Messages"
    ensure_dir(log_dir)

    log_dir = get_valid_filename(client.user.name) + os.sep + "Private_Group_Messages"
    ensure_dir(log_dir)
    return

    for private_channel in private_channels:
        """
        Private channels can be with one user, or a group message.
        If it's just a user, there can only be one conversation. So we use their username for it.
        If it's a group DM:
            If a name exists, don't use that - it can change. Instead, we use the usernames.
            There can be multiple group convos with the same users if they are created, so we need to use an identifier for this.
            We use the names, and the group DM id.
        """
        if len(private_channel.recipients) == 1:
            #One user message
            log_fname = private_channel.user.name
            log_dir = get_valid_filename(client.user.name) + os.sep + "Private_Messages" + os.sep + get_valid_filename(log_fname)
        else:
            #Group Message
            log_fname = '-'.join([user.name for user in private_channel.recipients]) + "-" + private_channel.id
            log_dir = get_valid_filename(client.user.name) + os.sep + "Private_Group_Messages" + os.sep + get_valid_filename(log_fname)

        ensure_dir(log_dir)
        """
        This is where we left off. Ensure directories for these and anything else
        we need to have a good name.        
        """

def list_find(e, l):
    i = 0
    for check in l:
        if check == e:
            i+=1
    return i

def search_strings(query, strings):
    """
    Arguments:
        query: A string to search our list of strings with.
        strings: A list of strings to search with our query.

    Returns:
        Does the following process:
        1. Converts query and all strings in list to lowercase, 
        2. Substitutes all non-alphanumeric characters for spaces (only in the strings),
        2. Divides query and all strings into list of words by splitting on space
        4. For every string list in our strings list, 
            check how many words match the words in our query and store both the integer "score" of that string, 
            and the index of our original string in a new list, with the format [score, index].
        5. Sort our original list of strings with the primary key as the score, and the secondary key as the original index.
        6. Only add entries which have scores of <= 0, and add the original index when adding an entry.

        So it returns indices for easy refererence, sorted by how closely each indices' associated string matched the query.
    """
    
    #Convert both to lowercase, replace all non-alphanumeric characters with spaces in the strings ONLY, and split our query and strings on spaces
    query = query.lower().split()
    strings = [re.sub(r"[^a-zA-Z0-9]", " ", s.lower()).split() for s in strings]

    #Initialize our empty lists
    search_info = []
    search_results = []

    #Loop through strings with index
    for i, string in enumerate(strings):
        #Start new empty entry for score and index for this string
        search_info.append([0,i])
        for query_word in query:
            #Get score of string
            search_info[i][0] += list_find(query_word, string)
    
    #Loop in descending order, using our scores as the primary key and original index as the secondary key
    for sorted_result in reversed(sorted(search_info)):
        #Get our score
        score = sorted_result[0]

        #Get the index of the original string which obtained this score
        string_i = sorted_result[1]

        #Check to ensure we only return results with a positive score.
        if score > 0:
            #Return the original index of this result for easy reference
            search_results.append(string_i)

    return search_results

def regex_messages(client, regex_query, return_full_message=False):
    """
    Arguments:
        client: A discord.py Client Object
        regex_query: A regex string to use with python's re library, so it should be a valid string with that library.
            Example: regex_query = r"[^A-Z]"
        return_full_message: 
            If True, this function will return the entire message containing a match for our regex, 
                and information about if the matching message was from a channel in a server, a private message, or private group message. 
                It will do this out of all logfiles searched.
            If False, this function will only return a list of the strings which our regex matched,
                out of all logfiles searched.

    Returns:
        Will go through all already existing logfiles under the client's username, 
            and return all matches from all logfiles using our regex_query for each logfile.
        if return_full_message=True,
            Will add on information about if the matching message was from a channel in a server,
                a private message, or private group message.
        if return_full_message=False,
            It will only return the section matching our regex.
        Since we may be connected to a lot of different servers and channels, or overrall
            may just have a fuckton of messages, we don't want to try loading all messages from 
            all connected channels into memory at once. So instead, we loop through all existing logfiles
            to do it one logfile at a time.
        This function is currently not asynchronous, though that may change.
    """
    #Initialize results list for all results
    results = []

    #Start looping through logfile filepaths
    for fpath in recursive_get_paths(client.user.name):
        """
        First we loop through all messages in our file at fpath,
            and add any matches to our matches list.
        If we have return_full_message=True, we will add the entire message,
            and add the preceding server + channel or private message data later.
        If we have return_full_message=False, we will only add the matching portion.
        """
        #Initialize results list for just this log
        log_results = []

        #Loop through messages/lines in our log file
        with open(fpath, "r") as f:
            for message in f:
                message = message.strip()

                #Our results for just this message
                message_results = re.findall(regex_query, message)

                #We have matches
                if len(message_results) > 0:
                    if return_full_message:
                        #Add entire message
                        log_results.append(message)
                    else:
                        #Add each regex match
                        log_results.extend(message_results)
        
        #We only need metadata_info if we are returning the full message, and also have messages to add the metadata info to
        if return_full_message and len(log_results) > 0:
            """
            Since each fpath may be something like "Private_Messages/kirito.log", or "Servers/Bot_Testing/general.log",
                and we may want to add on an indicator to the front of each message if it's a match(if return_full_message=True),
                we will parse out the information from the filepath.
            Once parsed, we will format the new message string as such:
                1. If it's a message from a Server's channel: 
                    Server: Bot_Testing, Channel: general, Message: 2017-06-08 23:02:50-DarkElement#1281: One, two three
                2. If it's a message from a Private message or group message:
                    Private Message: DarkElement, Message: 2017-06-08 22:47:17-DarkElement#1281: test
            """
            fpath = fpath.split(os.sep)

            try:
                if fpath[-3] == get_valid_filename(client.user.name):
                    """
                    Username folder is 2 behind our file, like DarkElement/Private_Messages/kirito.log
                        This means our file is from a private message / channel.
                    So we get our information from the filepaths and filenames.
                    """
                    private_message = fpath[-1][:-4]
                    metadata_info = "Private Message: %s, Message: " % (private_message)

                elif fpath[-4] == get_valid_filename(client.user.name):
                    """
                    Username folder is 3 behind our file, like DarkElement/Servers/Bot_Testing/general.log
                        This means our file is from a server.
                    So we get our information from the filepaths and filenames.
                    """
                    server = fpath[-2]
                    channel = fpath[-1][:-4]
                    metadata_info = "Server: %s, Channel: %s, Message: " % (server, channel)
            except:
                """
                In case this is called in a weird directory, we don't want to refer to indices outside of our list.
                """
                pass

            """
            Great, now we have metadata_info to precede our actual message with, if we are going to return the full message and have messages to use it with.
            Now we loop through all log_results (if return_full_message=True) and set them to metadata_info + message (or metadata_info + log_results[i], they are equivalent).
            """
            for i, message in enumerate(log_results):
                log_results[i] = metadata_info + message

        """
        At this point we are done with this logfile / fpath, 
            so we add all our log_results to our main results list,
            and continue to the next file.
        """
        results.extend(log_results)

    """
    At this point we've gone through every file.
    Unfortunately, if we have groups in our regex query, we will have tuples of each group's results instead of strings.
        Since we don't want this, we loop through and get rid of such groups - comcatenating all string(s) inside each tuple
    This also will only be necessary if return_full_message=False, we check for that.
    """
    if not return_full_message:
        for i,result in enumerate(results):
            results[i] = ''.join(result)

    #And with that, we're done.
    return results



def query_messages(client, query_str, return_full_message=False):
    """
    Arguments:
        client: A discord.py Client Object
        query_str: A query string, we will use this to search through all logfiles for matches of this string.
        return_full_message: 
            If True, this function will return the entire message containing a match for our query, 
                and information about if the matching message was from a channel in a server, a private message, or private group message. 
                It will do this out of all logfiles searched.
            If False, this function will only return a list of the strings which our query matched,
                out of all logfiles searched.

    Returns:
        This function is literally one line to call regex_messages using our query_str to create a regex_query.
        So check the documentation there if you want to know how it works.
        We use \S*query_str\S* as our regex string, as it checks for any instances of our query string in another string, excluding bordering spaces.
    """
    return regex_messages(client, r"\S*%s\S*"%(query_str), return_full_message=return_full_message)










































