from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools.translate import _
from odoo.tests.common import Form
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class BaseArchive(models.AbstractModel):
    _name = 'base.archive'
    active = fields.Boolean(default=True)
    
    def do_archive(self):
        for record in self:
            record.active = not record.active

class LibraryBook(models.Model):
    _inherit = ['base.archive']
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'date_release desc, name'
    _rec_name = 'short_name'
    old_edition = fields.Many2one('library.book', string='Old Edition')
    isbn = fields.Char('ISBN')
    manager_remarks = fields.Text('Manager Remarks')
    short_name = fields.Char('Short Title')
    date_return = fields.Date('Date to return')
    notes = fields.Text('Internal Notes')
    state = fields.Selection(
        [('draft', 'Unavailable'),
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('lost', 'Lost')],
        'State', default="draft")
    description = fields.Html('Description')
    publisher_city = fields.Char(
        'Publisher City',
        related='publisher_id.city',
        readonly=True)
    cost_price = fields.Float('Book Cost', digits='Book Price')
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price')
    cover = fields.Binary('Book Cover')
    ouy_of_print = fields.Boolean('Out of Print?')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages')
    pages1 = fields.Integer('N of Pages')
    name = fields.Char('Title', required=True)
    date_release = fields.Date('Release Date')
    category_id = fields.Many2one('library.book.category')

    reader_rating = fields.Float(
        'Reader Average Rating',
        digits=(14,4)
    )
    publisher_id = fields.Many2one(
        'res.partner', string='Publisher',
        ondelete='set null',
        context={},
        domain=[],
    )

    author_ids = fields.Many2many(
        'res.partner',
        string='Authors'
    )
    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)',
            'Book title must be unique.'),
        ('positive_page', 'CHECK(pages>0)',
            'No of pages must be positive')
    ]
    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=True
    )

    def return_all_books(self):
        self.ensure_one()
        wizard = self.env['library.return.wizard']
        wizard.create({
            'borrower_id': self.env.user.partner_id.id
        }).books_returns()

    def average_book_occupation(self):
        self.flush()
        sql_query = """
            SELECT
                lb.name,
                avg((EXTRACT(epoch from age(return_date, rent_date)) / 86400))::int
            FROM
                library_book_rent AS lbr
            JOIN
                library_book as lb ON lb.id = lbr.book_id
            WHERE lbr.state = 'returned'
            GROUP BY lb.name;"""
        self.env.cr.execute(sql_query)
        result = self.env.cr.fetchall()
        _logger.info("Average book occupation: %s", result)

    def make_lost(self):
        self.ensure_one()
        self.state = 'lost'
        if not self.env.context.get('avoid_deactivate'):
            self.active = False

    def book_rent(self):
        self.ensure_one()
        if self.state != 'available':
            raise UserError(_('Book is not available for renting'))
        rent_as_superuser = self.env['library.book.rent'].sudo()
        rent_as_superuser.create({
            'book_id': self.id,
            'borrower_id': self.env.user.partner_id.id,
        })

    def find_book(self):
        domain = [
            '|',
                '&', ('name', 'ilike', 'Book Name'),
                    ('category_id.name', 'ilike', 'Category Name'),
                '&', ('name', 'ilike', 'Book Name 2'),
                    ('category_id.name', 'ilike', 'Category Name 2'),
        ]
        books = self.search(domain)
        print(books)


    def change_release_date(self):
        self.ensure_one()
        self.date_release = fields.Date.today()
        
    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = d

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        operator_map = {'>:<', '>=:<=', '<:>', '<=:>=',}
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]

    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                msg = _('Moving from %s to %s is not allowed') % (book.state, new_state)
                raise UserError(msg)


    def make_available(self):
        self.change_state('available')

    def make_borrowed(self):
        self.change_state('borrowed')

    def make_lost(self):
        self.change_state('lost')

    def log_all_library_members(self):
        library_member_model = self.env['library.member']
        all_members = library_member_model.search([])
        print("ALL MEMBERS:", all_members)
        return True
    
        
    def write(self, values):
        if not self.user_has_groups('my_library.group_librarian'):
            if 'manager_remarks' in values:
                raise UserError(
                    'You are not allowed to modify manager remarks'
                )
        return super(LibraryBook, self).write(values)

    def name_get(self):
        result = []
        for book in self:
            authors = book.author_ids.mapped('name')
            name = '%s (%s)' % (book.name, ', '.join(authors))
            result.append((book.id, name))
            return result
    
    @api.model
    def _update_book_price(self):
        all_books = self.search([])
        for book in all_books:
            book.cost_price += 10

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = [] if args is None else args.copy()
        if not(name == '' and operator == 'ilike'):
            args += ['|', '|',
                    ('name', operator, name),
                    ('isbn', operator, name),
                    ('author_ids.name', operator, name)]
        return super(LibraryBook, self)._name_search(
            name=name, args=args, operator=operator, 
            limit=limit, name_get_uid=name_get_uid)

    @api.model
    def create(self, values):
        if not self.user_has_groups('my_library.group_librarian'):
            if 'manager_remarks' in values:
                raise UserError(
                    'You are not allowed to modify manager remarks'
                )
        return super(LibraryBook, self).create(values)

    @api.model
    def sort_books_by_date(self, books):
        return books.sorted(key='release_date')

    @api.model
    def get_author_names(self, books):
        return books.mapped('author_ids.name')

    @api.model
    def books_with_multiple_authors(self, all_books):
        def predicate(book):
            if len(book.author_ids) > 1:
                return True
            return False
        return all_books.filter(predicate)

    @api.constrains('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delta = today-book.date_release
                book.age_days = delta.days
            else:
                book.age_days = 0

    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].search([
            ('field_id.name', '=', 'message_ids')])
        return [(x.model, x.name) for x in models]

    ref_doc_id = fields.Reference(
        selection='_referencable_models',
        string='Reference Document'
    )

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if record.date_release and record.date_release > fields.Date.today():
                raise models.ValidationError(
                    'Release date must be in the past'
                )

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'available'),
                    ('available', 'borrowed'),
                    ('borrowed', 'available'),
                    ('available', 'lost'),
                    ('borrowed', 'lost'),
                    ('lost', 'available')]
        return (old_state, new_state) in allowed

    def get_average_cost(self):
        grouped_result = self.read_group(
            [('cost_price', "!=", False)],
            ['category_id', 'cost_price:avg'], 
            ['category_id']
        )
        return grouped_result


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = 'name'
    authored_book_ids = fields.Many2many(
        'library.book', string='Authored Books')
    count_books = fields.Integer('Number of Authored Books', compute='_compute_count_books')
    published_books_id = fields.One2many(
        'library.book', 'publisher_id',
        string='Published Books'
    )
    authored_book_ids = fields.Many2many(
        'library.book',
        string='Authored Books'
    )
    @api.depends('authored_book_ids')
    def _compute_count_books(self):
        for r in self:
            r.count_books = len(r.authored_book_ids)

class LibraryMember(models.Model):
    _name = 'library.member'
    _inherits = {'res.partner':'partner_id'}
    partner_id = fields.Many2one(
        'res.partner',
        ondelete='cascade')
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of birth')

class BookCategory(models.Model):
    _name = 'library.book.category'
    name = fields.Char('Category')
    description = fields.Text('Description')