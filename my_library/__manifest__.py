{
	'name': 'My Library',
	'summary': 'Manage books easily',
	'description': """
		Description related to library.
	""",
	'author': 'Your name',
	'website': 'http://www.example.com',
	'category': 'Uncategorized',
	'version': '13.0.1.0.1',
	'depends': ['base', 'product', 'stock'],
	'demo': ['data/demo.xml',],
	'data':[
		'views/library_book.xml',
		'data/data.xml',
		'views/library_book_rent.xml',
		'views/library_book_category.xml',
		'security/groups.xml',
		'wizard/library_book_rent_wizard.xml',
		'wizard/library_book_return_wizard.xml',
		'views/library_book_statistics.xml',
		'security/ir.model.access.csv',
		'views/authored_books_res.xml',
		'views/res_config_settings_views.xml'],
	'post_init_hook': 'add_book_hook',
}
