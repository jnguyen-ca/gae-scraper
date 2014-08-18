jQuery(document).ready(function($) {
	$('.month-input, .day-input, .year-input').on('keydown', function(e) {
		// Allow: backspace, delete, tab, escape
        if ($.inArray(e.keyCode, [46, 8, 9, 27, 37, 39]) !== -1)
        {
             // let it happen, don't do anything
             return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
	})
	$('.month-input').attr('placeholder', 'MM').on('keyup', function() {
		if (parseInt($(this).val(), 10) < 10 && parseInt($(this).val(), 10) > 0 && $(this).val().length < 2)
		{
			$(this).val('0' + $(this).val())
		}
		else if (parseInt($(this).val(), 10) > 12)
		{
			$(this).val('')
		}
		else if ($(this).val().length > 2)
		{
			$(this).val($(this).val().substring(1))
		}
	})
	$('.day-input').attr('placeholder', 'DD').on('keyup', function() {
		if (parseInt($(this).val(), 10) < 10 && parseInt($(this).val(), 10) > 0 && $(this).val().length < 2)
		{
			$(this).val('0' + $(this).val())
		}
		else if (parseInt($(this).val(), 10) > 31)
		{
			$(this).val('')
		}
		else if ($(this).val().length > 2)
		{
			$(this).val($(this).val().substring(1))
		}
	})
	$('.year-input').attr('placeholder', 'YYYY').on('keyup', function() {
		if (parseInt($(this).val(), 10) > 9999)
		{
			$(this).val('')
		}
	})
	
	$('.season-display-control').on('change', function() {
		var $hiddenControl = $(this).parent().find('.season-display-hidden-control')
		$(this).is(':checked') ? $hiddenControl.removeAttr('checked') : $hiddenControl.attr('checked','checked');
	})
	
	$('.add-season-button').on('click', function() {
		if ($(this).hasClass('add-season-button'))
		{
			$(this)
				.removeClass('add-season-button')
				.addClass('submit-season-button')
				.text('Submit Season')
				.siblings('.add-season-inputs')
				.show()
		}
		else if ($(this).hasClass('submit-season-button'))
		{
			var fromMonth = $(this).siblings('.add-season-inputs').find('.from-inputs .month-input').val()
			var fromDay = $(this).siblings('.add-season-inputs').find('.from-inputs .day-input').val()
			var fromYear = $(this).siblings('.add-season-inputs').find('.from-inputs .year-input').val()
			var toMonth = $(this).siblings('.add-season-inputs').find('.to-inputs .month-input').val()
			var toDay = $(this).siblings('.add-season-inputs').find('.to-inputs .day-input').val()
			var toYear = $(this).siblings('.add-season-inputs').find('.to-inputs .year-input').val()
			
			if (fromMonth.length == 2 && fromDay.length == 2 && fromYear.length == 4
					&& toMonth.length == 2 && toDay.length == 2 && toYear.length == 4)
			{
				var league = $(this).closest('.league-row').find('.league-title').text()
				var dateRange = fromMonth+'.'+fromDay+'.'+fromYear+'-'+toMonth+'.'+toDay+'.'+toYear
				
				$(this).parent().append(
					$('<div></div>')
						.addClass('season-control')
						.append(
							$('<input>').attr('type', 'checkbox').addClass('season-display-control').attr('name', 'season-display-control').attr('checked','checked').val(league+'&'+dateRange).on('change', function() {
								var $hiddenControl = $(this).parent().find('.season-display-hidden-control')
								$(this).is(':checked') ? $hiddenControl.removeAttr('checked') : $hiddenControl.attr('checked','checked');
							})
						)
						.append('<span class="season-label">'+dateRange+'</span>')
						.append(
							$('<input>').attr('type', 'checkbox').addClass('season-display-hidden-control').attr('name', 'season-display-hidden-control').val(league+'&'+dateRange).hide()
						)
				)
			}
			
			$(this)
				.removeClass('submit-season-button')
				.addClass('add-season-button')
				.text('Add Season')
				.siblings('.add-season-inputs')
				.hide()
				.find('input')
				.val('')
		}
	});
});