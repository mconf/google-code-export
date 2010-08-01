import os, re
from xml.dom import minidom

class XmlWriter:
    
    def __init__(self, project, filename=None):
        
        if not filename:
            filename = project + '_google-code-export.xml'
        
        self.filename = filename

        self.doc = minidom.Document()
        self.rootXml = self.doc.createElement('googleCodeExport')
        self.doc.appendChild(self.rootXml)

        self.issuesXml = self.doc.createElement('issues')
        self.rootXml.appendChild(self.issuesXml)

    def appendTextNode(self, parent, node, text):
        nodeXml = self.doc.createElement(node)
        parent.appendChild(nodeXml)

        textXml = self.doc.createTextNode(text)
        nodeXml.appendChild(textXml)

        return nodeXml

    def appendIssue(self, issue):
        # append an issue as xml
        issueXml = self.doc.createElement('issue')
        self.issuesXml.appendChild(issueXml)

        # put small data in attributes
        issueXml.attributes['id'] = str(issue.id)
        issueXml.attributes['stars'] = str(issue.stars)
        
        self.appendTextNode(issueXml, 'summary', issue.summary)
        self.appendTextNode(issueXml, 'status', issue.status)
        self.appendTextNode(issueXml, 'reporter', issue.reporter)
        self.appendTextNode(issueXml, 'reportDate', str(issue.report_date))

        if issue.merge_into:
            self.appendTextNode(issueXml, 'mergeInto', str(issue.merge_into))

        if issue.owner:
            self.appendTextNode(issueXml, 'owner', issue.owner)

        if issue.close_date:
            self.appendTextNode(issueXml, 'closeDate', str(issue.close_date))
        
        if issue.labels and len(issue.labels) > 0:
            labelsXml = self.doc.createElement('labels')
            issueXml.appendChild(labelsXml)
            
            for label in issue.labels:
                self.appendTextNode(labelsXml, 'label', label)

        if issue.relations and len(issue.relations) > 0:
            relationsXml = self.doc.createElement('relations')
            issueXml.appendChild(relationsXml)
            
            for relation in issue.relations:
                relationXml = self.doc.createElement('relation')
                relationsXml.appendChild(relationXml)

                relationXml.attributes['type'] = relation.getTypeString()
                relationXml.attributes['id'] = str(relation.id)
        
        self.appendAttachments(issueXml, issue.attachments)

        self.appendTextNode(issueXml, 'details', issue.details)

        if issue.comments and len(issue.comments) > 0:
            commentsXml = self.doc.createElement('comments')
            issueXml.appendChild(commentsXml)
            
            for comment in issue.comments:
                self.appendComment(commentsXml, comment)

    def appendAttachments(self, parentXml, attachments):
        if attachments and len(attachments) > 0:
            attachmentsXml = self.doc.createElement('attachments')
            parentXml.appendChild(attachmentsXml)
            
            for attachment in attachments:
                attachmentXml = self.appendTextNode(
                    attachmentsXml, 'attachment', attachment.url)
                
                attachmentXml.attributes['filename'] = attachment.filename

    def appendComment(self, commentsXml, comment):
        commentXml = self.doc.createElement('comment')
        commentsXml.appendChild(commentXml)

        commentXml.attributes['id'] = str(comment.id)
        commentXml.attributes['author'] = comment.author
        commentXml.attributes['date'] = str(comment.date)
        
        if comment.new_status:
            commentXml.attributes['newStatus'] = comment.new_status
        
        if comment.new_owner:
            commentXml.attributes['newOwner'] = comment.new_owner
        
        if comment.owner_removed:
            commentXml.attributes['ownerRemoved'] = str(True)
        
        if comment.merged_with:
            commentXml.attributes['mergedWith'] = str(comment.merged_with)
        
        if comment.new_summary:
            self.appendTextNode(commentXml, 'newSummary', comment.new_summary)
        
        self.addCommentLabels(
            commentXml, comment.labels_added, 'labelsAdded')
        
        self.addCommentLabels(
            commentXml, comment.labels_removed, 'labelsRemoved')
        
        self.appendAttachments(commentXml, comment.attachments)

        if comment.text:
            # wrap in a text file, since this isn't the only thing
            # we can have in a google code comment.
            self.appendTextNode(commentXml, 'text', comment.text)

    def addCommentLabels(self, commentXml, labels, nodeText):
        if labels and len(labels) > 0:
            nodeXml = self.doc.createElement(nodeText)
            commentXml.appendChild(nodeXml)
                    
            for label in labels:
                self.appendTextNode(nodeXml, 'label', label)
                        
    def save(self):
        # remove extra whitespace added by pretty print. alternate regex:
        #   fix = re.compile(r'((?)(n[t]*)(?=[^<t]))|(?t])(n[t]*)(?=<)')
        #   fixed_output = re.sub(fix, '', input_string)
        uglyXml = self.doc.toprettyxml(indent='  ')
        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        prettyXml = text_re.sub('>\g<1></', uglyXml)

        # HACK: for some reason, newl='\n' (toprettyxml arg) does not work.
        prettyXml = prettyXml.replace('\r\n', '\n')

        file = open(self.filename, 'w')
        file.write(prettyXml)
        file.close()

        print 'wrote: ' + self.filename

class RedmineWriter:
    pass
