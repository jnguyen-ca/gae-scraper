function getZeroPaddedOptions(len) {
	/* Get simple integer value options */
	var options = {}
	
	for (var i=1;i<=len;i++)
	{
		options[i] = i.toString()
		if (options[i].length < 2)
		{
			options[i] = '0'.concat(options[i])
		}
	}
	
	return options
}

function getDayOptions(month, year) {
	/* Get the day options based on month and year */
	var dayOptions;
	
	if (['Apr', 'Jun', 'Sep', 'Nov'].indexOf(month) >= 0)
	{
		dayOptions = getZeroPaddedOptions(30)
	}
	else if (month == 'Feb') 
	{
		year = parseInt(year,10)
		if (year % 400 == 0 || (year % 4 == 0 && year % 100 != 0))
		{
			dayOptions = getZeroPaddedOptions(29)
		}
		else
		{
			dayOptions = getZeroPaddedOptions(28)
		}
	}
	else
	{
		dayOptions = getZeroPaddedOptions(31)
	}
	
	return dayOptions
}

function populateDayOptions(monthSelect) {
	/* Change the amount of day options based on month */
	var $monthSelect = $(monthSelect)
	var $daySelect = $monthSelect.parent().siblings('.day').children('select')
	var selectedMonth = $monthSelect.find('option:selected').text()
	var selectedYear = $monthSelect.parent().siblings('.year').children('select').find('option:selected').val()
	var dayOptions = getDayOptions(selectedMonth, selectedYear)
	
	$daySelect.empty()
	$.each(dayOptions, function(val, text) {
		$daySelect.append('<option value="'+val+'">'+text+'</option')
	})
}

function setFilterValues(league, $filter) {
	var leagueFilterValues = $.parseJSON($('#filter-template').children('.filter-values').val())[league]
	
	$.each($filter, function() {
		var dataFilterKey = $(this).attr('data-filter-key')
		
		if (leagueFilterValues.hasOwnProperty(dataFilterKey)) {
			var $selectMenu = $(this).children('select')
			$selectMenu.empty()
			$('<option></option>').attr('value', 'All').text('All').appendTo($selectMenu)
			filterValues = leagueFilterValues[dataFilterKey]
			for (var i=0;i<filterValues.length;i++) {
				filterValue = filterValues[i]
				$('<option></option>').attr('value', filterValue).text(filterValue).appendTo($selectMenu)
			}
		}
	})
}

jQuery(document).ready(function($) {
	var $filterForm = $('#filter-form')
	var $filterTemplate = $('#filter-template')
	
	// only do this the first time
	if ($filterTemplate.hasClass('empty-template'))
	{
		var date = new Date()
		var year = date.getFullYear()
		
		var monthOptions = {
				01 : 'Jan',
				02 : 'Feb',
				03 : 'Mar',
				04 : 'Apr',
				05 : 'May',
				06 : 'Jun',
				07 : 'Jul',
				08 : 'Aug',
				09 : 'Sep',
				10 : 'Oct',
				11 : 'Nov',
				12 : 'Dec',
		}
		
		// populate the month select
		var $monthSelect = $filterTemplate.find('.filter-date .month select')
		$.each(monthOptions, function(val, text) {
			$monthSelect.append('<option value="'+val+'">'+text+'</option')
		})
		
		// populate the year select from 2014 to current year+1
		var $yearSelect = $filterTemplate.find('.filter-date .year select')
		for (var i=parseInt($yearSelect.find('option:first').val(),10);i<=year+1;i++)
		{
			$yearSelect.append('<option value="'+i+'">'+i+'</option')
		}
		$filterTemplate.find('.filter-date .end-date .year select').val(year+1)
		
		// populate the day options whenever month is changed
		$monthSelect.each(function() {populateDayOptions(this)})
		$monthSelect.on('keyup change', function() {populateDayOptions(this)})
		
		var $superLeagueSelect = $filterTemplate.find('.super-league-filter select')
		setFilterValues($superLeagueSelect.val(), $superLeagueSelect.parent().nextAll('.filter'))
		$superLeagueSelect.on('change', function() {setFilterValues($(this).val(), $(this).parent().nextAll('.filter'));})
		
		// don't want to set these properties again (in case of page refresh)
		$filterTemplate.removeClass('empty-template').addClass('filled-template')
		
		function copyTemplate(appendElement) {
			$templateCopy = $filterTemplate.children('.filter-set').clone(true)
			
			function incrementDateId(filterClass) {
				var $dateInput = $templateCopy.find('.filter-date .'+filterClass+' input')
				var newInputId = $dateInput.prop('id').slice(0, -2) + '0' + (parseInt($dateInput.prop('id').substr(-2),10) + 1)
				$dateInput.attr('id', newInputId).siblings('label').prop('for', newInputId)
			}
			
			incrementDateId('disable-date')
			incrementDateId('enable-date')
			
			$templateCopy.appendTo(appendElement)
		}
		
		copyTemplate($filterForm)
		
		// TEST
		$.ajax({
			url: '/dashboard',
			type: 'POST',
			data: 'test',
			success: function(data, text, jqXHR) {
				console.log(data)
				console.log(text)
			}
		})
	}
});