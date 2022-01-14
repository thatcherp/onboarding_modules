from odoo import models, fields
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'date_release desc, name'
    _rec_name = 'short_name'
    short_name = fields.Char('Short Title', required=True)
    notes = fields.Text('Internal Notes')
    state = fields.Selection(
        [('draft', 'Not Available'),
        ('available', 'Available'),
        ('lost', 'Lost')],
        'State')
    description = fields.Html('Description')
    cost_price = fields.Float('Book Cost', digits='Book Price')
    cover = fields.Binary('Book Cover')
    ouy_of_print = fields.Boolean('Out of Print?')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages')
    name = fields.Char('Title', required=True)
    date_release = fields.Date('Release Date')
    reader_rating = fields.Float(
        'Reader Average Rating',
        digits=(14,4)
    )
    author_ids = fields.Many2many(
        'res.partner',
        string='Authors'
    )