def delete_tags(re, string):
    return re.sub('<a.*?a>','',string)