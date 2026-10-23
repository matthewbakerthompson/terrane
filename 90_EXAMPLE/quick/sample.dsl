// A workspace someone already has: the Structurizr "Big Bank" example, cut down.
workspace "Big Bank plc" "An example workspace, read as a sketch." {

    !identifiers hierarchical

    model {
        customer = person "Personal Banking Customer" "A customer of the bank, with personal bank accounts." "Customer"

        group "Big Bank plc" {
            mainframe = softwareSystem "Mainframe Banking System" "Stores all of the core banking information about customers, accounts, transactions, etc." "Existing System"
            email = softwareSystem "E-mail System" "The internal Microsoft Exchange e-mail system." "Existing System"

            internetBanking = softwareSystem "Internet Banking System" "Allows customers to view information about their bank accounts, and make payments." {
                web = container "Web Application" "Delivers the static content and the Internet banking single page application." "Java and Spring MVC"
                spa = container "Single-Page Application" "Provides all of the Internet banking functionality to customers via their web browser." "JavaScript and Angular" "Web Browser"
                mobile = container "Mobile App" "Provides a limited subset of the Internet banking functionality to customers via their mobile device." "Xamarin" "Mobile App"
                api = container "API Application" "Provides Internet banking functionality via a JSON/HTTPS API." "Java and Spring MVC"
                database = container "Database" "Stores user registration information, hashed authentication credentials, access logs, etc." "Oracle Database Schema" "Database"
            }
        }

        # relationships between people and software systems
        customer -> internetBanking.web "Visits bigbank.com/ib using" "HTTPS"
        customer -> internetBanking.spa "Views account balances, and makes payments using"
        customer -> internetBanking.mobile "Views account balances, and makes payments using"
        email -> customer "Sends e-mails to"

        # relationships to/from containers
        internetBanking.web -> internetBanking.spa "Delivers to the customer's web browser"
        internetBanking.spa -> internetBanking.api "Makes API calls to" "JSON/HTTPS"
        internetBanking.mobile -> internetBanking.api "Makes API calls to" "JSON/HTTPS"
        internetBanking.api -> internetBanking.database "Reads from and writes to" "JDBC"
        internetBanking.api -> mainframe "Makes API calls to" "XML/HTTPS"
        internetBanking.api -> email "Sends e-mail using" "SMTP"
    }

    views {
        container internetBanking "Containers" {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                shape person
            }
            element "Database" {
                shape cylinder
            }
        }
    }
}
