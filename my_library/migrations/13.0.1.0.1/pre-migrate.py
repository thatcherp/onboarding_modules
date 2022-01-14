def migrate(cr, version):
    cr.execute('ALTER TABEL library_book RENAME COLUMN date_release TO date_release_char')