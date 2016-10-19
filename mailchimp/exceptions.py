class ChimpException(Exception): pass

class MCCampaignDoesNotExist(ChimpException): pass
class MCListDoesNotExist(ChimpException): pass
class MCConnectionFailed(ChimpException): pass
class MCTemplateDoesNotExist(ChimpException): pass
class MCFolderDoesNotExist(ChimpException): pass

class MailchimpWarning(Warning): pass
