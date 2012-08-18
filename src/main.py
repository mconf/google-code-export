from gcexport import parsers, writers
from time import sleep
import getopt, sys
import os.path

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'p:s:c:l:')
    except getopt.GetoptError, err:
        print 'error:', str(err)
        usage()
        exit(2)

    project = None
    start = None
    count = None
    label = None

    for o, a in opts:
        if o == '-p':
            project = a
        elif o == '-s':
            start = int(a)
        elif o == '-c':
            count = int(a)
        elif o == '-l':
            label = a

    if not project:
        print 'error: project name missing'
        usage()
        exit(2)

    if not start:
        print 'error: start id missing'
        usage()
        exit(2)

    if not count:
        print 'error: count missing'
        usage()
        exit(2)

    writer = writers.XmlWriter(project)
    parser = parsers.IssueParser(project)

    for i in range(start, start + count):
        issue = parser.parse(i)
        if issue:
            if label:
                if parser.matches_label(label, issue):
                    writer.appendIssue(issue)
            else:
                writer.appendIssue(issue)
        else:
            print 'no issue found!'

    writer.save()

def usage():
    print 'usage: main.py -p <project-name> -s <start-id> -c <count>'

if __name__ == "__main__":
    main()
