jQuery(document).ready(function($) {
	var $formTemplates = $('#form_templates')
	
	function gameRowControlsScripts($game_row) {
		$game_row.find('.tip-controls').hover(
				function() {$(this).closest('.game_row').addClass('tip_controls-hover')},
				function() {$(this).closest('.game_row').removeClass('tip_controls-hover')}
		)
		
		// generic tip controls button click
		$game_row.find('.tip-controls input').on('click', function() {
			var $control_input = $(this)
			
			var $game_row = $control_input.closest('.game_row')
			if ($game_row.children('form').length > 0) {
				$game_row.children('form').remove()
				return false
			}
			
			// get the request's form by using the button's name attribute
			var request_type = $control_input.attr('name')
			var $tempForm = $formTemplates.find('.'+request_type+'-form').clone().addClass('tempForm').appendTo($game_row)
			
			$tempForm.on('submit', function() {
				var $this = $(this)
				$.ajax({
					url 	 : '/display',
					type	 : 'POST',
					data	 : $this.serialize(),
					success  : function(data, text, jqXHR) {
						if (data) {
							// updated game row from server, attach scripts to it then insert into html
							var $data = $(data)
							gameRowControlsScripts($data)
							$data.insertAfter($game_row)
							$('.updated-highlight').removeClass('updated-highlight')
							$data.addClass('updated-highlight')
						}
						$game_row.remove()
					},
					error: function(jqXHR, text, data) {
//						console.log(jqXHR.responseText)
						$game_row.addClass('error-highlight')
						// revert all the form inputs so to initial state (not the values) so that they can be submitted again
						$tempForm.find('.unchanged-on-submit').each(function() {
							var $this = $(this)
							var unchanged_name = $this.attr('name')
							$this.attr('name', unchanged_name.substr(0, unchanged_name.lastIndexOf('-unchanged')))
								.removeClass('unchanged-on-submit')
						})
						// changed checkboxes were checked so that they could be sent in request so go through all
						// checkboxes to change/ensure checked status represents their value
						$tempForm.find('[type="checkbox"]').each(function() {
							var $this = $(this)
							if ($this.val() === 'false') {
								this.checked = false
							}
							else if ($this.val() === 'true') {
								this.checked = true
							}
						})
					},
				})
				return false
			});
			
			// form input values which have the class tip-data are inputs that can be filled
			// their name attribute corresponds with the game_row's children's classes
			$tempForm.children('.tip-data').each(function() {
				var $input = $(this)
				var name_identifier = $input.attr('name')
				var $game_row_element = $game_row.find('.'+name_identifier)
				
				$input.val($game_row_element.html())
				
				// turn editable form inputs into editable inputs
				if ($input.hasClass('editable')) {
					// handle the different cases of inputs
					if ($input.hasClass('string-data')) {
						$input.attr('type', 'text')
					}
					else if ($input.hasClass('integer-data')) {
						$input.attr('type', 'number')
					}
					else if ($input.hasClass('boolean-data')) {
						// booleans are checkboxes which require a little bit of special functionality
						// want a label, for the label we need the input to have an id so generate a unique id
						function guid() {
						    var S4 = function() {
						       return (((1+Math.random())*0x10000)|0).toString(16).substring(1);
						    };
						    return (S4()+S4()+"-"+S4()+"-"+S4()+"-"+S4()+"-"+S4()+S4()+S4());
						}
						var input_guid = name_identifier+'-'+guid()
						
						$input.attr('type', 'checkbox').attr('id', input_guid).on('change', function() {
							$input.val(this.checked)
							
							// every time elapsed/archived status is changed make sure the other one
							// corresponds correctly to the new change
							// i.e. cannot be archived if not elapsed, cannot be not elapsed if archived
							// and to also set the value of the input so that it can be passed to the server
							if (name_identifier == 'status-archived') {
								if (this.checked) {
									$input.siblings('[name="status-elapsed"]').prop('checked', true).trigger('change')
								}
							}
							else if (name_identifier == 'status-elapsed') {
								if (!this.checked) {
									$input.siblings('[name="status-archived"]').prop('checked', false).trigger('change')
								}
							}
						})
						
						if ($input.val() === 'true') {
							this.checked = true
						}
						
						var label = name_identifier.substr(name_identifier.indexOf('-')+1)
						$('<label>')
							.attr('for',input_guid)
							.html(label.charAt(0).toUpperCase() + label.slice(1))
							.insertBefore($input)
					}
					else if ($input.hasClass('datetime-data')) {
						$input.attr('type', 'datetime-local')
					}
				}
			})
			
			var tip_date_teams_label = $game_row.find('.game_time-MST').html()+' '+$game_row.find('.participant-away').html()+' @ '+$game_row.find('.participant-home').html()
			// handle different requests
			if (request_type == 'delete-tip') {
				if (confirm('Remove '+tip_date_teams_label+' tip?')) {
					$tempForm.submit()
				}
				else {
					$tempForm.remove()
				}
			}
			else if (request_type == 'edit-tip') {
				$tempForm.find(':submit').on('click', function(event) {
					// before submitting want to set the form up so that only values
					// that are being explicitly changed are sent to the server to be processed
					// also want a confirmation box listing all the fields being changed
					// so delay submission of form for now
					event.preventDefault()
					
					// find out what's actually being changed
					var change_list = []
					$tempForm.children('.editable').each(function() {
						var $input = $(this)
						var name_identifier = $input.attr('name')
						var $game_row_element = $game_row.find('.'+name_identifier)
						
						if ($input.val() != $game_row_element.html()) {
							if (!($input.val() == '' && $game_row_element.length == 0)) {
								change_list.push(name_identifier)
							}
						}
					})
					
					if (change_list.length) {
						// confirm the list of fields to be changed
						message = 'You are changing: '+"\n"
						for (var i=0;i<change_list.length;i++) {
							message += '        '+$game_row.find('.'+change_list[i]).attr('name')+"\n"
						}
						message += 'for the tip: '+tip_date_teams_label
						
						if (confirm(message)) {
							// only fields that are being changed should be of interest for the server
							// however want to keep the inputs in case of an error so that don't have to
							// remake the form, therefore just change the unchanged input's names to something
							// server won't recognize
							$tempForm.children('.editable').each(function() {
								var $input = $(this)
								var name_identifier = $input.attr('name')
								
								if (change_list.indexOf(name_identifier) < 0) {
									$input.attr('name',name_identifier+'-unchanged').addClass('unchanged-on-submit')
								}
								else if ($input.attr('type') == 'checkbox') {
									// checkbox values only get sent in request if they're checked
									// so change checked status without changing value
									$input.prop('checked', true)
								}
							})
							
							$tempForm.submit()
						}
					}
					else {
						alert('Nothing changed!')
					}
				})
			}
		});
	}
	
	$('.game_row').each(function() {
		gameRowControlsScripts($(this))
	})
});