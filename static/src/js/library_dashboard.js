/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class LibraryDashboard extends Component{
    setup(){
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.MostIssue = useRef("most_issued")
        this.ReturnedToday = useRef("return_today")
        this.ExpiresTomorrow= useRef("expires_tomorrow")
        this.MembershipExpiresToday= useRef("membership_expires_today")
        this.state = useState({
                books_count : null,
                borrowed_books : null,
                returned_books : null,
                issued_books : null,
                members : null,
                expired_books : null,
                late_members : null,
                authors : null,
                popular_book : null,
                top_reader:null,
        });
        onWillStart(async () => {
            await this.fetch_data();
        });
        onMounted(async ()=> {
            await this.render_most_issue_books();
            await this.render_books_expire_today();
            await this.render_books_expire_tomorrow();
            await this.render_membership_expires_today();
        });
    }
    // Fetch data to the tiles
    async fetch_data() {
        var self = this
        var result = await this.orm.call( 'product.template', "get_data",[])
        var popular_result = await this.orm.call( 'product.template', "get_most_popular_books",[])
        this.state.popular_book = popular_result
        this.state.top_reader = await this.orm.call('book.register', 'get_top_readers',[])
        console.log(this.state.top_reader)
        this.state.books = result['books_count']
        this.state.borrowed_books = result['borrowed_books']
        this.state.returned_books = result['returned_books']
        this.state.issued_books = result['issued_books']
        this.state.members = result['members']
        this.state.expired_books = result['expired_books']
        this.state.late_members = result['late_members']
        this.state.authors = result['authors']
    }
    // Action for view the books
    onClickBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Books",
            res_model: 'product.template',
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
            domain: "[('is_a_book', '=', True)]"
        });
    }
    // Action for view the list of borrowed books
    onClickBorrowed() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Borrowed",
            view_mode: "kanban,list,form",
            res_model: 'book.register',
            views: [[false, "list"], [false, "form"],[false,"kanban"]],
            target: "current",
        });
    }
    onCreateNewBook(){
    this.action.doAction({
            type: "ir.actions.act_window",
            name: "createBook",
            view_mode: "form",
            res_model: 'product.product',
            views: [ [false, "form"]],
            target: "current",
            context: {
            default_is_a_book: true,
        },
        });
    }

    onCreatePublisher(){
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "createPublisher",
            view_mode: "form",
            res_model: 'book.publisher',
            views: [ [false, "form"]],
            target: "current",
        });
    }
    onCreateNewMember(){
    this.action.doAction({
            type: "ir.actions.act_window",
            name: "createMember",
            view_mode: "form",
            res_model: 'res.partner',
            views: [ [false, "form"]],
            target: "current",
        });
    }
    onIssueBook(){
    this.action.doAction({
            type: "ir.actions.act_window",
            name: "createMember",
            view_mode: "form",
            res_model: 'book.register',
            views: [ [false, "form"]],
            target: "current",
        });
    }
    onAllBookView(){
    this.action.doAction({
            type: "ir.actions.act_window",
            name: "view all book",
            view_mode: "list",
            res_model: 'product.template',
            views: [ [false, "list"]],
            target: "current",
            domain : "[('is_a_book', '=', True)]",

        });
    }

    // Action for view the list of returned books
    onClickReturned() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Returned",
            res_model: 'book.register',
            views: [ [false,"kanban"],[false, "list"], [false, "form"]],
            target: "current",
            domain: "[('register_status', '=', 'returned')]"
        });
    }
    // Action for view the list of issued books
    onClickIssued() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Issue",
            res_model: 'book.register',
            views: [ [false, "list"], [false, "form"]],
            target: "current",
            domain: "[('register_status', '=', 'issued')]"
        });
    }
    // Action to view all the members in the library
    onClickMembers() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Members",
            res_model: 'res.partner',
            views: [[false,"kanban"],[false, "list"], [false, "form"]],
            target: "current",
            domain: "[('is_a_member', '=', True)]"
        });
    }
    // Action to view all the expired books in the library
    onClickExpiredBooks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Expired Books",
            res_model: 'book.register',
            views: [ [false,"kanban"],[false, "list"], [false, "form"]],
            target: "current",
            domain: "[('register_status', '=', 'expired')]"
        });
    }
    // Action to view all the late members of the library
    async onClickLateMembers() {
        const memberIds = await this.orm.call("res.partner", "get_late_member_ids",[]);
        // Create and execute the action with the fetched domain
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Late Members",
            res_model: 'res.partner',
            views: [[false, "kanban"], [false, "form"]],
            target: "current",
            domain: [['id', 'in', memberIds]],
            create: false,
            edit: false,
        });
    }
    // Action to view all the authors of the library
    onClickAuthors() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Authors",
            res_model: 'book.author',
            views: [[false, "list"], [false, "form"],[false,"kanban"]],
            target: "current"
        });
    }
    onBookClick(BookId) {
    this.action.doAction({
        type: "ir.actions.act_window",
        name: "Popular Books",
        res_model: "product.template",
        view_mode: "form",
        res_id: BookId,
        views: [[false, "form"]],
        target: "current",
    });
}


    // To view the top issue books in the chart
    async render_most_issue_books() {
        var self = this
        var ctx = this.MostIssue.el;
        const arrays = await this.orm.call('product.template', "get_most_issue_books",[])
        var data = {
            labels : arrays[1],
            datasets: [{
                label: "",
                data: arrays[0],
                backgroundColor: [
                    "#1E90FF",
                    "#95B9C7",
                    "#66CDAA",
                    "#FF7F50",
                    "#F67280",
                    "#810541",
                    "#7D0552",
                    "#D58A94",
                    "#B041FF"
                ],
                borderColor: [
                    "#1E90FF",
                    "#95B9C7",
                    "#66CDAA",
                    "#FF7F50",
                    "#F67280",
                    "#810541",
                    "#7D0552",
                    "#D58A94",
                    "#B041FF"
                ],
                borderWidth: 1,
                tension: 0.1
            },]
        };
        //options
        var options = {
            responsive: true,
            title: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            onClick: function(event, elements) {
                if (elements.length > 0) {
                    var index = elements[0].index;
                    self.redirectToBookView(arrays[2][index]);
                }
            }
        };
        //create Chart class object
        var chart = new Chart(ctx, {
            type: "line",
            data: data,
            options: options
        });
    }
    // Redirect to the each book view while clicking on the line chart
    redirectToBookView(bookId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Books',
            res_model: 'product.template',
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [['id', '=', bookId]],
            target: 'current'
        });
    }
    // To view the issue books that going to expire today
    async render_books_expire_today() {
        var self = this
        var ctx = this.ReturnedToday.el;
        const arrays = await this.orm.call('book.register', "get_books_expires_today",[])
        var data = {
            labels : arrays[1],
            datasets: [{
                label: "",
                data: arrays[0],
                backgroundColor: [
                    "#1E90FF",
                    "#95B9C7",
                    "#66CDAA",
                    "#FF7F50",
                    "#F67280",
                    "#810541",
                    "#7D0552",
                    "#D58A94",
                    "#B041FF"
                ],
                borderColor: [
                    "#1E90FF",
                    "#95B9C7",
                    "#66CDAA",
                    "#FF7F50",
                    "#F67280",
                    "#810541",
                    "#7D0552",
                    "#D58A94",
                    "#B041FF"
                ],
                borderWidth: 1
            },]
        };
        //options
        var options = {
            responsive: true,

            title: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                yAxes: [{
                    gridLines: {
                        color: "rgba(0, 0, 0, 0)",
                        display: false,
                    },
                    ticks: {
                        min: 0,
                        display: false,
                    }
                }]
            },
            onClick: function(event, elements) {
                if (elements.length > 0) {
                    var index = elements[0].index;
                    self.redirectToExpiresBooks(arrays[2][index]);
                }
            }
        };
        //create Chart class object
        var chart = new Chart(ctx, {
            type: "bar",
            data: data,
            options: options
        });
    }
    // Redirect to the each book which is going to be expire while clicking on the bar chart
    redirectToExpiresBooks(bookId) {
        const currentDate = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Expired Books',
            res_model: 'book.register',
            views: [ [false, "list"], [false, "form"]],
            domain: [['book_id', '=', bookId], ['calc_return_date', '=', currentDate]],
            target: 'current'
        });
    }
    // To view the issue books that going to expire tomorrow
    async render_books_expire_tomorrow() {
        var self = this
        var ctx = this.ExpiresTomorrow.el;
        const arrays = await this.orm.call( 'book.register', "get_books_expire_tomorrow",[])
        var data = {
            labels : arrays[1],
            datasets: [{
                label: "",
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],

            },]
        };
        //options
        var options = {
            responsive: true,
             aspectRatio: 1.5,
            maintainAspectRatio: false,
            layout: {
                padding: 10
            },
            plugins: {
                tooltip: { enabled: true },
                legend: { display: false }, // disable default legend
                cutout: '10%'
            },

            title: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        fontColor: "#333",
                        fontSize: 12
                    }
                },
            },
            scales: {
                yAxes: [{
                    gridLines: {
                        color: "rgba(0, 0, 0, 0)",
                        display: false,
                    },
                    ticks: {
                        min: 0,
                        display: false,
                    }
                }]
            }
        };
        //create Chart class object
        var chart = new Chart(ctx, {
            type: "doughnut",
            data: data,
            options: options
        });
    }
    // To view the Membership that going to expire today
    async render_membership_expires_today() {
        var self = this
        var ctx = this.MembershipExpiresToday.el;
        const arrays = await this.orm.call( 'res.partner', "get_membership_expires_today",[])
        var data = {
            labels : arrays[1],
            datasets: [{
                label: "",
                data: arrays[0],
                backgroundColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],
                borderColor: [
                    "#003f5c",
                    "#2f4b7c",
                    "#f95d6a",
                    "#665191",
                    "#d45087",
                    "#ff7c43",
                    "#ffa600",
                    "#a05195",
                    "#6d5c16"
                ],

            },]
        };
        //options
        var options = {
            maintainAspectRatio: false,
             aspectRatio: 1,
            responsive: true,
            title: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        fontColor: "#333",
                        fontSize: 12
                    }
                },
            },
            scales: {
                yAxes: [{
                    gridLines: {
                        color: "rgba(0, 0, 0, 0)",
                        display: false,
                    },
                    ticks: {
                        min: 0,
                        display: false,
                    }
                }]
            },
            onClick: function(event, elements) {
                if (elements.length > 0) {
                    var index = elements[0].index;
                    self.redirectToExpiresMembership(arrays[2][index]);
                }
            }
        };
        //create Chart class object
        var chart = new Chart(ctx, {
            type: "pie",
            data: data,
            options: options
        });
    }
    // Redirect to the each book which is going to be expire while clicking on the bar chart
    redirectToExpiresMembership(memberId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Memebership Expired',
            res_model: 'res.partner',
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [['id', '=', memberId]],
            target: 'current'
        });
    }
}
LibraryDashboard.template = 'LibraryDashboard'
registry.category("actions").add("library_dashboard_tag", LibraryDashboard)

