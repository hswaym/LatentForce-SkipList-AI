import orders
import dispatch


def main():
    order_id = orders.create_order("ITEM-123", 99.50)
    result = dispatch.run_action("export")
    print(f"Order {order_id} processed with result: {result}")


if __name__ == "__main__":
    main()
