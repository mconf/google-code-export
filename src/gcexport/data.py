class Issue:
    comments = None
    labels = None
    close_date = None
    owner = None
    merge_into = None
    relations = None
    attachments = None

class IssueComment:
    text = None
    new_status = None
    new_owner = None
    owner_removed = False
    labels_added = None
    labels_removed = None
    new_summary = None
    merged_with = None
    attachments = None

class IssueRelation:
    BLOCKS = 1

    def getTypeString(self):
        if self.type == self.BLOCKS:
            return 'Blocks'
        else:
            raise Exception('Unknown type: ' + self.type)

class IssueAttachment:
    pass
