openerp.edydsi_branch_pos = function(instance){
    var module   = instance.point_of_sale;

    baseOrder = module.Order

    module.Order = baseOrder.extend({
        generateUniqueId: function(){
            res = baseOrder.prototype.generateUniqueId.apply(this);

            function zero_pad(num,size){
                var s = ""+num;
                while (s.length < size) {
                    s = "0" + s;
                }
                return s;
            };
            this.ticket_reference = zero_pad(this.pos.config.branch_legal_id || 0, 3) + '-' +
                                    zero_pad(this.pos.config.pos_legal_id || 0, 3) + '-' +
                                    zero_pad(this.sequence_number + (this.pos.config.sales_point.sequence_next || 0) - 1, 8);
            this.ticket_sales_point = this.pos.config.sales_point;

            return res;
        },

        export_for_printing: function(){
            res = baseOrder.prototype.export_for_printing.apply(this);
            res.ticket_reference = this.ticket_reference;
            return res;
        },
        export_as_JSON: function() {
            res = baseOrder.prototype.export_as_JSON.apply(this);
            res.ticket_reference = this.ticket_reference;
            return res;
        },

        getTotalExentas: function(){
            return (this.get('orderLines').filter(function(orderLine){
                    return orderLine.get_tax() == 0;        
                })).reduce((function(sum, orderLine) {
                    return sum + orderLine.get_price_with_tax();
                }), 0);
        },
        getTotalGravadas: function(){
            return (this.get('orderLines').filter(function(orderLine){
                    return orderLine.get_tax() > 0;        
                })).reduce((function(sum, orderLine) {
                    return sum + orderLine.get_price_with_tax();
                }), 0);
        },
        getTotalByTax: function(taxName){
            tbid = this.pos.taxes_by_id;
            return (this.get('orderLines').filter(function(orderLine){
                    for(var id in orderLine.get_tax_details()){
                        if (tbid[id].name == taxName){
                            return true;
                        };
                    };
                    return false;
                })).reduce((function(sum, orderLine) {
                    return sum + orderLine.get_price_with_tax();
                }), 0);
        },
        getArticleCount: function(){
            count = 0;
            (this.get('orderLines')).each(function(orderLine){
                uom = orderLine.get_unit();
                if (uom.name == 'Unidad(es)'){
                    count += orderLine.get_quantity();
                }
                else {
                    count += 1;
                }
            });
            return count;
        },
        getTicketReference: function(){
            return this.ticket_reference;
        },
        getTaxTotal: function(){
            taxes = 0.0;
            (this.get('orderLines')).each(function(orderLine){
                taxes += orderLine.get_tax();
            });
            return taxes;
        },

    });

    module.PaymentScreenWidget = module.PaymentScreenWidget.extend({
        validate_order: function(options) {
            var self = this;
            options = options || {};

            var currentOrder = this.pos.get('selectedOrder');

            if(currentOrder.get('orderLines').models.length === 0){
                this.pos_widget.screen_selector.show_popup('error',{
                    'message': _t('Empty Order'),
                    'comment': _t('There must be at least one product in your order before it can be validated'),
                });
                return;
            }

            if(!this.is_paid()){
                return;
            }

            // The exact amount must be paid if there is no cash payment method defined.
            if (Math.abs(currentOrder.getTotalTaxIncluded() - currentOrder.getPaidTotal()) > 0.00001) {
                var cash = false;
                for (var i = 0; i < this.pos.cashregisters.length; i++) {
                    cash = cash || (this.pos.cashregisters[i].journal.type === 'cash');
                }
                if (!cash) {
                    this.pos_widget.screen_selector.show_popup('error',{
                        message: _t('Cannot return change without a cash payment method'),
                        comment: _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                    });
                    return;
                }
            }

            if (this.pos.config.iface_cashdrawer) {
                    this.pos.proxy.open_cashbox();
            }

            if (!currentOrder.get_client() && this.pos.config.anonymous_customer){
                currentOrder.set_client(this.pos.config.anonymous_customer);
            }

            if(options.invoice){
                // deactivate the validation button while we try to send the order
                this.pos_widget.action_bar.set_button_disabled('validation',true);
                this.pos_widget.action_bar.set_button_disabled('invoice',true);

                var invoiced = this.pos.push_and_invoice_order(currentOrder);

                invoiced.fail(function(error){
                    if(error === 'error-no-client'){
                        self.pos_widget.screen_selector.show_popup('error',{
                            message: _t('An anonymous order cannot be invoiced'),
                            comment: _t('Please select a client for this order. This can be done by clicking the order tab'),
                        });
                    }else{
                        self.pos_widget.screen_selector.show_popup('error',{
                            message: _t('The order could not be sent'),
                            comment: _t('Check your internet connection and try again.'),
                        });
                    }
                    self.pos_widget.action_bar.set_button_disabled('validation',false);
                    self.pos_widget.action_bar.set_button_disabled('invoice',false);
                });

                invoiced.done(function(){
                    self.pos_widget.action_bar.set_button_disabled('validation',false);
                    self.pos_widget.action_bar.set_button_disabled('invoice',false);
                    self.pos.get('selectedOrder').destroy();
                });

            }else{
                var invoiced = this.pos.push_and_invoice_reference(currentOrder);

                invoiced.fail(function(error){
                    self.pos_widget.screen_selector.show_popup('error',{
                        message: _t('The order could not be sent'),
                        comment: _t('Check your internet connection and try again.'),
                    });
                    self.pos_widget.action_bar.set_button_disabled('validation',false);
                    self.pos_widget.action_bar.set_button_disabled('invoice',false);
                });

                invoiced.done(function(){
                    if(self.pos.config.iface_print_via_proxy){
                        var receipt = currentOrder.export_for_printing();
                        self.pos.proxy.print_receipt(QWeb.render('XmlReceipt',{
                            receipt: receipt, widget: self,
                        }));
                        self.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
                    }else{
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    }
                });
            }

            // hide onscreen (iOS) keyboard 
            setTimeout(function(){
                document.activeElement.blur();
                $("input").blur();
            },250);
        },

    });

    baseOrderLine = module.Orderline
    module.Orderline = baseOrderLine.extend({
        getTaxNames: function(){
            var taxes = [];
            for (var id in this.get_tax_details()) {
                taxes.push(this.pos.taxes_by_id[id].name);
            };
            return taxes;
        },
    });

    module.PosModel.prototype.models.push({
        model:  'res.branch',
        fields: ['name','street','city'],
        domain: function(self){ return [['id','=', self.config.branch[0]]]; },
        loaded: function(self,branches){
            self.branches = branches;
            var branches_by_id = {};
            for(var i = 0, len = branches.length; i < len; i++){
                branches_by_id[branches[i].id] = branches[i];
            }
            self.branches_by_id = branches_by_id;
            self.config.branch = self.branches_by_id[self.config.branch[0]];
        }
     });

    module.PosModel.prototype.models.push({
        model:  'res.sales_point',
        fields: ['name','sequence_next'],
        domain: function(self){ return [['id','=', self.config.sales_point[0]]]; },
        loaded: function(self,sales_points){
            self.sales_points = sales_points;
            var sales_points_by_id = {};
            for(var i = 0, len = sales_points.length; i < len; i++){
                sales_points_by_id[sales_points[i].id] = sales_points[i];
            }
            self.sales_points_by_id = sales_points_by_id;
            self.config.sales_point = self.sales_points_by_id[self.config.sales_point[0]];

            if (self.config.anonymous_customer){
                self.config.anonymous_customer = {
                    id: self.config.anonymous_customer[0],
                    name: self.config.anonymous_customer[1],
                };
                for (var idx = 0, len = self.partners.length; i < len; i++){
                    var partner = self.partners[idx];
                    if (partner.id == self.config.anonymous_customer.id) {
                        self.config.anonymous_customer = partner;
                        break;
                    }
                }
            }
        }
    });

    module.PosModel = module.PosModel.extend({
        push_and_invoice_reference: function(order){
            var self = this;
            var invoiced = new $.Deferred(); 

            if(!order.get_client()){
                invoiced.reject('error-no-client');
                return invoiced;
            }

            var order_id = this.db.add_order(order.export_as_JSON());

            this.flush_mutex.exec(function(){
                var done = new $.Deferred(); // holds the mutex

                // send the order to the server
                // we have a 30 seconds timeout on this push.
                // FIXME: if the server takes more than 30 seconds to accept the order,
                // the client will believe it wasn't successfully sent, and very bad
                // things will happen as a duplicate will be sent next time
                // so we must make sure the server detects and ignores duplicated orders

                order.invoice_id = {
                    id: 0,
                    number: '---------',
                };

                var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:30000, to_invoice:true});
                
                transfer.fail(function(){
                    invoiced.reject('error-transfer');
                    done.reject();
                });

                // on success, get the order id generated by the server
                transfer.pipe(function(order_server_id){    

                    var posOrderModel = new instance.web.Model('pos.order');
                    posOrderModel.call('invoice_ref', 
                                              order_server_id
                        ).then(function (invoice_refs) {
                            for (var key in invoice_refs){
                                order.invoice_id=invoice_refs[key];
                            }
                            invoiced.resolve();
                            done.resolve();
                        }).fail(function (error, event){
                            if(error.code === 200 ){    // Business Logic Error, not a connection problem
                                self.pos_widget.screen_selector.show_popup('error-traceback',{
                                    message: error.data.message,
                                    comment: error.data.debug
                                });
                            }
                            // prevent an error popup creation by the rpc failure
                            // we want the failure to be silent as we send the orders in the background
                            event.preventDefault();
                            console.error('Failed to send orders:', orders);
                            invoiced.reject('error-transfer');
                            done.reject();
                        });
                });

                return done;

            });

            return invoiced;
        },

        // send an array of orders to the server
        // available options:
        // - timeout: timeout for the rpc call in ms
        // returns a deferred that resolves with the list of
        // server generated ids for the sent orders
        // MODIFIED TO SEND default_branch and default_sales_point in context

        _save_to_server: function (orders, options) {
            if (!orders || !orders.length) {
                var result = $.Deferred();
                result.resolve([]);
                return result;
            }
                
            options = options || {};

            var self = this;
            var timeout = typeof options.timeout === 'number' ? options.timeout : 7500 * orders.length;

            // we try to send the order. shadow prevents a spinner if it takes too long. (unless we are sending an invoice,
            // then we want to notify the user that we are waiting on something )
            var posOrderModel = new instance.web.Model('pos.order');
            return posOrderModel.call('create_from_ui',
                [_.map(orders, function (order) {
                    order.to_invoice = options.to_invoice || false;
                    return order;
                })],
                {context:{
                     default_branch: self.config.branch.id,
                     default_sales_point: self.config.sales_point.id,
                    },
                },
                {
                    shadow: !options.to_invoice,
                    timeout: timeout
                }
            ).then(function (server_ids) {
                _.each(orders, function (order) {
                    self.db.remove_order(order.id);
                });
                return server_ids;
            }).fail(function (error, event){
                if(error.code === 200 ){    // Business Logic Error, not a connection problem
                    self.pos_widget.screen_selector.show_popup('error-traceback',{
                        message: error.data.message,
                        comment: error.data.debug
                    });
                }
                // prevent an error popup creation by the rpc failure
                // we want the failure to be silent as we send the orders in the background
                event.preventDefault();
                console.error('Failed to send orders:', orders);
            });
        },


    });

};

  