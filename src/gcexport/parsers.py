from BeautifulSoup import BeautifulSoup, SoupStrainer
import urllib, re, data
from datetime import datetime, date

class IssueParser:
    
    url_format = 'http://code.google.com/p/%s/issues/detail?id=%i'
    
    def __init__(self, project):
        self.project = project

    def parse(self, id, savePage=False):
        url = self.url_format % (self.project, id)
        print 'parse: %s' % url
        
        usock = urllib.urlopen(url)
        data = usock.read()
        usock.close()
        
        if savePage:
            # save last downloaded page to file
            f = open('last.html', 'w')
            f.write(data)
            f.close()

        soup = BeautifulSoup(data)
        return self.parseSoup(soup)
    
    def regexFirst(self, soup_result, regex, group=1, default=None):
        if soup_result and len(soup_result) > 0:
            match = regex.search(soup_result[0].string)
            if match:
                return match.group(group)
        
        return default
    
    def parseSoup(self, soup):
        issue = data.Issue()
        
        id_match = re.search('Issue (\d+) -', soup.title.string)
        if id_match:
            issue.id = int(id_match.group(1))
        else:
            # unlikely to be more data if no id found
            return None
        
        summary_match = re.search(' (.*) - Project.*', soup.title.string)
        if summary_match:
            issue.summary = summary_match.group(1)
        
        # get the number that preceeds "people/person starred", or 0 stars
        # if there's no text at all)
        stars_regex = re.compile('(\d+) (people|person) starred')
        stars_soup = soup.findAll('td', text=stars_regex)
        issue.stars = int(self.regexFirst(stars_soup, stars_regex, default=0))
        
        # reporter is within the <a> that follows "Reported by"
        reporter_soup = soup.find('div', 'author', text='\n Reported by ')
        issue.reporter = reporter_soup.findNext('a').renderContents()
        
        # report date is within the <span> title attribute after the reporter
        issue.report_date = datetime.strptime(
            reporter_soup.findNext('span')['title'], '%a %b %d %H:%M:%S %Y')

        # status is within the next <span> that follows "Status: "
        status_soup = soup.find('th', text='Status:&nbsp;')
        issue.status = status_soup.findNext('span').renderContents()

        # merge info follows the status in the same pattern (but within <a>)
        merge_soup_th = status_soup.findNext('th', text='Merged:&nbsp;')
        if merge_soup_th:
            merge_soup_a = merge_soup_th.findNext('td').find('a')
            # remove the "issue " prefix (we just want the id)
            issue.merge_into = int(merge_soup_a.renderContents().replace(
                'issue ', ''))

        # owner follows the status in the same pattern (but within <a>)
        owner_th = status_soup.findNext('th', text='Owner:&nbsp;')
        owner_a = owner_th.findNext('td').find('a')
        if owner_a:
            issue.owner = owner_a.renderContents()

        # closed date follows on after owner (add year so we get full date)
        close_date_th = owner_th.findNext('th', text='Closed:&nbsp;')
        if close_date_th:
            issue.close_date = self.parseCloseDate(close_date_th)

        labels_soup = soup.findAll('a', href=re.compile('list\?q=label:'))
        if labels_soup:
            issue.labels = []
            for label_soup in labels_soup:
                # get rid of those <b> tags and add to the statuses
                issue.labels.append(
                    ''.join(label_soup.findAll(text=True)))

        # TODO: there might be other types of related issues
        rel_issues_div = soup.find('div', 'rel_issues')
        if rel_issues_div:
            issue.relations = []
            
            blocking_b = rel_issues_div.find('b', text='Blocking:')
            if blocking_b:
                # it seems that google only got round to implementing 1 type
                # of issue relation (blocking). duplicates info is not really
                # rendered in the same way, which is weird.
                for issue_a in rel_issues_div.findAll('a'):
                    text_id = issue_a.renderContents().replace('issue ', '')
                    blocks = data.IssueRelation()
                    blocks.type = data.IssueRelation.BLOCKS
                    blocks.id = int(text_id)
                    issue.relations.append(blocks)

        # attachments exist in the description area
        desc_td = soup.find('td', 'vt issuedescription')
        issue.attachments = self.parseAttachments(desc_td)

        # all pre tags are details and comments
        pre_tags = soup.findAll('pre')
        if pre_tags:
            # first pre tag is always the details value
            issue.details = pre_tags[0].renderContents().strip()
            
            if len(pre_tags) > 1:
                issue.comments = []
                
                # all following pre tags are comments
                for pre in pre_tags[1:]:
                    comment = self.parseComment(pre)
                    if comment:
                        issue.comments.append(comment)

        return issue

    def parseAttachments(self, td):
        attach_div = td.find('div', 'attachments')
        if attach_div:
            attachments = []
            for attach_table in attach_div.findAll('table'):
                attach_b = attach_table.find('b')
                attach_a = attach_table.find('a', text='Download').parent
                
                attach = data.IssueAttachment()
                attach.filename = attach_b.renderContents()
                attach.url = attach_a['href']
                attachments.append(attach)
            return attachments
        else:
            return None

    def parseComment(self, pre):
        text = pre.renderContents().strip()              
        if text:
            comment = data.IssueComment()
            
            # clean up google's silly empty comments. this is valid
            # because users often reference other comments, so
            # we should persist google's silly empty comments.
            if text.find('(No comment was entered for this change.)') == -1:
                if text.find('has been merged into this issue.') == -1:
                    comment.text = text
                else:
                    # comment describes an issue merge
                    a_content = pre.find('a').renderContents().strip()
                    comment.merged_with = int(a_content.replace('Issue ', ''))
            
            # author is fairly simple, just the last <a> contents
            comment.author = pre.findPrevious('a').renderContents()

            # date is just the last <span> title attribute
            comment.date = datetime.strptime(
                pre.findPrevious('span')['title'],
                '%a %b %d %H:%M:%S %Y')

            # within the <td> for this comment, look for a changes box
            changes_soup = pre.parent.find('div', 'box-inner')
            if changes_soup:
                changes = changes_soup.renderContents().split('<br />')
                
                for change in changes:
                    labels_re = re.search('<b>Labels:</b> (.*)', change)
                    if labels_re:
                        labels = labels_re.group(1).split(' ')
                        comment.labels_removed = []
                        comment.labels_added = []
                        for label in labels:
                            # if it beings with -, then it's been removed
                            if label.find('-') == 0: 
                                comment.labels_removed.append(label[1:])
                            else:
                                comment.labels_added.append(label)

                    owner_re = re.search('<b>Owner:</b> (.*)', change)
                    if owner_re:
                        owner_text = owner_re.group(1)
                        if owner_text == '---':
                            comment.owner_removed = True
                        else:
                            comment.new_owner = owner_text

                    status_re = re.search('<b>Status:</b> (.*)', change)
                    if status_re:
                        comment.new_status = status_re.group(1)

                    summary_re = re.search('<b>Summary:</b> (.*)', change)
                    if summary_re:
                        comment.new_summary = summary_re.group(1)
            
            comment.attachments = self.parseAttachments(pre.parent)
            
            return comment
        else:
            return None

    def parseCloseDate(self, soup):
        close_date_text = soup.findNext(
            'td').renderContents().strip()
        
        if close_date_text == 'Today':
            return datetime.now().date()
        
        else:
            close_date_year = re.match('\w+ \d{4}', close_date_text)
            if close_date_year:
                # parse google's special date format: no day of month
                return datetime.strptime(
                    '01 ' + close_date_text, '%d %b %Y').date()
            else:
                # parse google's special date format: no year
                this_year = date.today().strftime(' %Y')
                return datetime.strptime(
                    close_date_text + this_year, '%b %d %Y').date()

# OBSOLETE (more!)
"""
from HTMLParser import HTMLParser
import urllib, re, data

class GoogleCodeIssueParser(HTMLParser):

    url_format = 'http://code.google.com/p/%s/issues/detail?id=%i'
    
    def __init__(self, project, id):
        HTMLParser.__init__(self)
        self.project = project
        self.issue = data.GoogleCodeIssue()
        self.id = id

    def parse(self):
        url = self.url_format % (self.project, self.id)
        print 'parse: %s' % url
        
        usock = urllib.urlopen(url)
        self.data = usock.read()
        usock.close()
        
        # save last downloaded page to file
        f = open('last.html', 'w')
        f.write(self.data)
        f.close()
        
        self.feed(self.data)

    def get_attr_value(self, attrs, key):
        value_arr = [v for k, v in attrs if k == key]
        if value_arr:
            return value_arr[0]
        else:
            return None

    def handle_starttag(self, tag, attrs):
        # if class is 'vt h3' then it's probably the issue number
        
        if tag == 'td':
            if self.get_attr_value(attrs, 'class') == 'vt h3':
                text = self.get_starttag_text()
                id_match = re.match(text, '.*Issue <a.*>(\d+)</a>.*')
                if id_match:
                    self.issue.id = id_match.group(1)

    def handle_endtag(self, tag):
        pass
"""

# OBSOLETE     
"""
class SpiderParserContext:
    issues = dict()
    visited = []
    depth = 0

    def __init__(self, project, max_depth, max_visits):
        self.project = project
        self.max_depth = max_depth
        self.max_visits = max_visits

class GoogleCodeSpiderParser(HTMLParser):

    PAGE_ROOT = 1
    PAGE_ISSUE_LIST = 2
    PAGE_ISSUE_DETAIL = 3

    gc_base_url = 'http://code.google.com'

    recurse_into = [
        ('.*/issues/(list$|list\?num=\d+.*start=\d+.*)', PAGE_ISSUE_LIST),
        ('.*/issues/detail\?id=\d+$', PAGE_ISSUE_DETAIL)
    ]
    
    def __init__(self, context, depth=1):
        HTMLParser.__init__(self)
        self.depth = depth
        self.context = context

        # used to record the depth actually reached
        if context.depth < depth:
            context.depth = depth

    def feedroot(self):
        self.feedurl(self.gc_base_url + '/p/' + self.context.project + '/')

    def feedurl(self, url):
        print 'visiting: ' + url
        self.start_url = url

        # set visited before hand (even though we haven't actually visited the
        # url yet) to stop recusion during feed.
        self.context.visited.append(url)
        
        sleep(0.5)
        usock = urllib.urlopen(url)
        self.feed(usock.read())
        usock.close()
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = [v for k, v in attrs if k == 'href']
            if href:
                # skip if we've already reached the max depth/visits
                if len(self.context.visited) >= self.context.max_visits:
                    print 'skipping, max visits reached'
                    return
                
                if self.depth >= self.context.max_depth:
                    print 'skipping, max depth reached'
                    return
                
                link = href[0]
                url = self.get_url(link)
                if not url in self.context.visited:
                    pt = self.page_type(url)
                    if pt:
                        parser = GoogleCodeSpiderParser(
                            self.context, self.depth + 1)
                        parser.feedurl(url)
                else:
                    print 'skipping already visited: ' + link

    def get_url(self, link):
        if link.startswith('http:') or link.startswith('https:'):
            return link
        elif link.startswith('/'):
            # if url starts with '/' then it's absolute
            return self.gc_base_url + link
        else:
            # otherwise, it's relative, so combine the start url and the link
            return self.start_url[:self.start_url.rfind('/') + 1] + link

    def page_type(self, url):
        for re_str, pt in self.recurse_into:
            print re_str
            print url
            if re.match(re_str, url):
                print 'hit'
                return pt
            else:
                print 'miss'
        return None
"""
