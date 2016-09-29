var mod = (function() {
	function itemSelected() {
		event.preventDefault();
		var item_blob = this.getElementsByTagName('h4');
		var item_no = item_blob[0].textContent,
			manu_no = item_blob[1].textContent;

		socket.send({"action": "module", "data": {"action": "item-no", "data": {"item-no": item_no, "manu-no": manu_no}}});
	}

	function lotSelected() {
		event.preventDefault();
		var item_blob = this.getElementsByTagName('h6');
		var lot_no = item_blob[0].textContent;

		socket.send({"action": "module", "data": {"action": "lot-no", "data": {"lot-no": lot_no}}});
	}

	function loadShipment() {
		event.preventDefault();
		var item_blob = this.getElementsByTagName('h2');
		var ship_no = item_blob[0].textContent.split(':')[0];

		socket.send({"action": "module", "data": {"action": "ship-no", "data": {"ship-no": ship_no}}});
	}

	return {
		processResponse: function processResponse(action, mydata) {
			if (action == 'qty-received' && mydata.hasOwnProperty('lot-no')) {
				var lot_buttons = document.querySelectorAll('#data div:not(.shipping-hedr) > button');
				for (var i = 0; i < lot_buttons.length; i++) {
					if (lot_buttons[i].getElementsByTagName('h6')[0].textContent == mydata['lot-no']) {
						lot_buttons[i].classList.add('completed');
						break;
					}
				}
			}
		},
		initialize: function initialize() {
			var scan_text = document.createElement('h1');
			scan_text.appendChild(document.createTextNode('Scan Now'));
			scan_text.style.color = '#0A4D8E';
			scan_text.style.textShadow = 'none';
			scan_text.style.margin = '15% 0';
			scan_text.style.minWidth = '100vw';
			scan_text.style.flexGrow = '1';
			scan_text.classList.add('rocking');
			data.appendChild(scan_text);
		},
		afterLoad: function afterLoad(module_data) {
			if (module_data.hasOwnProperty('type')) {
				var buttons, lot_buttons, ship_buttons, i;
				if (module_data['type'] == 'ticket') {
					buttons = document.querySelectorAll('#data button');
					main_app.attachButtonEvents(buttons);
					for (i = 0; i < buttons.length; i++) {
						buttons[i].addEventListener('touchstart', itemSelected, true);
						buttons[i].addEventListener('click', itemSelected, true);
					}
				} else if (module_data['type'] == 'item') {
					lot_buttons = document.querySelectorAll('#data div:not(.shipping-hedr) > button');
					main_app.attachButtonEvents(lot_buttons);
					for (i = 0; i < lot_buttons.length; i++) {
						lot_buttons[i].addEventListener('touchstart', lotSelected, true);
						lot_buttons[i].addEventListener('click', lotSelected, true);
					}
					ship_buttons = document.querySelectorAll('#data div.shipping-hedr > button');
					main_app.attachButtonEvents(ship_buttons);
					for (i = 0; i < ship_buttons.length; i++) {
						ship_buttons[i].addEventListener('touchstart', loadShipment, true);
						ship_buttons[i].addEventListener('click', loadShipment, true);
					}
				}
			}
		}
	};
})();
