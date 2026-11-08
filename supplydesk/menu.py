"""Interactive terminal adapter; business rules remain in OrderService."""


def money(cents):
    return f"${cents // 100}.{cents % 100:02d}"


def show_catalog(products):
    print("\nProduct ID       Name                     Price     Stock")
    for product in products:
        print(f"{product['product_id']:<16} {product['name']:<24} "
              f"{money(product['unit_price_cents']):>8} {product['stock']:>8}")


def show_order(order):
    print("\n" + order.get("order_id", "Quote") + " - " + order.get("status", "not placed"))
    print(f"Customer: {order['customer_type']} | Fulfillment: {order['fulfillment']}")
    for line in order['items']:
        print(f"  {line['name']} x {line['quantity']}: {money(line['line_total_cents'])}")
    for label, key in (("Subtotal", "subtotal_cents"), ("Discount", "discount_cents"),
                       ("Delivery", "delivery_cents"), ("Total", "total_cents")):
        print(f"{label}: {money(order[key])}")


def read_request(service):
    show_catalog(service.catalog())
    print("Enter product IDs from the table. Blank product ID finishes the item list.")
    customer = input("Customer type [regular/student] (Enter = regular): ").strip() or "regular"
    items = []
    while True:
        product_id = input("Product ID (Enter = finish): ").strip()
        if not product_id:
            break
        raw = input("Quantity: ").strip()
        try:
            quantity = int(raw)
        except ValueError:
            print("Please enter a whole number. Re-enter this item.")
            continue
        items.append({"product_id": product_id, "quantity": quantity})
    fulfillment = input("Fulfillment [pickup/delivery] (Enter = pickup): ").strip() or "pickup"
    return customer, items, fulfillment


def confirmed(prompt):
    return input(prompt + " [y/N]: ").strip().lower() == "y"


def view_catalog(service):
    show_catalog(service.catalog())


def get_quote(service):
    show_order(service.quote(*read_request(service)))
    print("Quote only: no stock reserved and no order created.")


def place_order(service):
    request = read_request(service)
    show_order(service.quote(*request))
    if confirmed("Place this order?"):
        show_order(service.place_order(*request))
    else:
        print("Order not placed.")


def view_history(service):
    orders = service.list_orders()
    if not orders:
        print("No orders yet.")
    for order in orders:
        show_order(order)


def find_order(service):
    show_order(service.get_order(input("Order ID: ").strip()))


def cancel_order(service):
    order_id = input("Order ID to cancel: ").strip()
    if confirmed("Cancel this order?"):
        show_order(service.cancel_order(order_id))
    else:
        print("Cancellation abandoned.")


# Menu number -> (label, handler). The printed menu and the dispatch both come from here.
MENU_OPTIONS = {
    "1": ("View products and stock", view_catalog),
    "2": ("Get a quote", get_quote),
    "3": ("Place an order", place_order),
    "4": ("View order history", view_history),
    "5": ("Find an order", find_order),
    "6": ("Cancel an order", cancel_order),
}
EXIT_OPTION = "0"


def menu_text():
    lines = [f"{key}. {label}" for key, (label, _) in MENU_OPTIONS.items()]
    return "\n" + "\n".join(lines) + f"\n{EXIT_OPTION}. Exit"


def run_menu(service):
    print("Campus Supply Desk | All prices are CAD. Orders are saved automatically.")
    while True:
        try:
            print(menu_text())
            choice = input("Choose an option: ").strip()
            if choice == EXIT_OPTION:
                print("Goodbye.")
                return 0
            if choice in MENU_OPTIONS:
                _, handler = MENU_OPTIONS[choice]
                handler(service)
            else:
                print(f"Choose a number from {EXIT_OPTION} to {len(MENU_OPTIONS)}.")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        except (ValueError, OSError, KeyError, TypeError) as error:
            print(f"Error: {error}")
            print("Returning to the menu. Check your input or state file before retrying.")
