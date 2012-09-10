project_settings = {
'ITEM_PIPELINES': ['project_modules.partylite.PartyliteImagesPipeline'],

'USERS_PRODUCTION': {'us' : 'serino',
                    'canada_en': 'partylitecanada',
                    'canada_fr': 'roselyneseney'
},

'USERS_DEVELOPMENT': {'us' : 'teri',
                    'canada_en': 'partylitetestfr',
                    'canada_fr': 'partylitetesteng'
},

'DEFAULT_CATALOG': 'Halloween',
# Images store is currently set to store in project root directory
# but can be done relative with this code below(first line is for getting parent
# directory, and second to join that with new folder for images )
# so it can be used to get any relative path needed

# parent = os.getcwd()
# fn = os.path.join(parent, 'images_sokos')

# path were pictures will be stored

'IMAGES_STORE': "images/cc855f80-a98f-11e1-afa6-0800200c9a66",

# this is to set how many days before images are treated as old and will be
# replaced on new scraper run if it's under set days old and that folder already
# has image with same name it won't replace it
'IMAGES_EXPIRES': 300

#IMAGES_THUMBS = {
#    'small': (50, 62)
#}
}
