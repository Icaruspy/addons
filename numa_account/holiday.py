#-*- coding: utf-8 -*-
##############################################################################
#
#    NUMA Extreme Systems (www.numaes.com)
#    Copyright (C) 2013
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv.osv import Model, TransientModel, except_osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp import tools
from datetime import datetime, timedelta, date

import logging
_logger = logging.getLogger(__name__)

class holiday(Model):
    _name = 'account.holiday'
    _rec_name = 'date'

    _columns = {
        'country': fields.many2one('res.country', 'Country', required=True),
        'date': fields.date('Date', required=True),
        'notes': fields.text('Notes'),
    }

    def name_get (self, cr, user, ids, context=None):
        if not context:
            context={}

        if isinstance(ids, list):
            names = []
            for hol in self.browse (cr, SUPERUSER_ID, ids, context=context):
                names.append((hol.id, "[%s-%s]" % (hol.country.code, hol.date)))
            return names
        else:
            hol = self.browse (cr, SUPERUSER_ID, ids)
            return (hol.id, "[%s-%s]" % (hol.country.code, hol.date))

    def count_laborable_days(self, cr, uid, country_id, from_date, upto_date, context=None):
        holiday_ids = self.search(cr, uid, 
                                    [('date','>=', from_date),('date', '<', upto_date), 
                                     ('country','=', country_id)], 
                                    order="date", 
                                    context=context)
        d_from_date = date(int(from_date[0:4]), int(from_date[5:7]), int(from_date[8:10]))
        d_upto_date = date(int(upto_date[0:4]), int(upto_date[5:7]), int(upto_date[8:10]))

        holidays = self.browse(cr, uid, holidays_ids, context=context)

        cd = d_from_date
        count = 0
        while cd < d_upto_date:
            if cd.weekday() not in [5, 6]:
                while holidays and holidays[0].date < cd.isoformat():
                    holidays.pop(0)
                if holidays and holidays[0].date > cd.isoformat():
                    count += 1
            cd += timedelta(days=1)

        return count

    def add_delta_to_date(self, cr, uid, country_id, from_date, delta_days, context=None):
        holiday_ids = self.search(cr, uid, 
                                    [('date','>=', from_date), ('country','=', country_id)], 
                                    order="date", 
                                    context=context)
        cd = date(int(from_date[0:4]), int(from_date[5:7]), int(from_date[8:10]))

        holidays = self.browse(cr, uid, holiday_ids, context=context)

        count = 0
        if delta_days >= 0:
            while count < delta_days:
                if cd.weekday() not in [5, 6]:
                    while holidays and holidays[0].date < cd.isoformat():
                        holidays.pop(0)
                    if holidays and holidays[0].date == cd.isoformat():
                        holidays.pop(0)
                    else:
                        count += 1
                cd += timedelta(days=1)
        elif delta_days == 0:
            while holidays and holidays[0].date < cd.isoformat():
                holidays.pop(0)
            while True:
                if holidays and holidays[0].date == cd.isoformat():
                    holidays.pop(0)
                elif cd.weekday() not in [5, 6]:
                    break
                cd += timedelta(days=1)
        else:
            holidays = sorted(holidays, key=lambda x: x.date, reverse=True)
            while count < delta_days:
                if cd.weekday() not in [5, 6]:
                    while holidays and holidays[0].date > cd.isoformat():
                        holidays.pop(0)
                    if holidays and holidays[0].date < cd.isoformat():
                        count += 1
                cd += timedelta(days=-1)

        return cd


