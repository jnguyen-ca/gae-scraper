jQuery(document).ready(function($) {
	var $formTemplates = $('#form_templates')
	
	function getAppKey($element) {
		return $element.closest('.app-variable').find('.app-title .app-key').text()
	}
	
	function getDictLevel($element) {
		return $element.closest('.dict-entries').children('.dict-level').val()
	}
	
	function getEntryKey($entry) {
		return ($entry.length < 1) ? '' : getEntryKey($entry.parent().closest('.dict-entry'))+'['+$entry.children('.dict-key').text()+']'
	}
	
	function addEditEntryForm(appKey, entryKey, entryValue, entryLevel, successHandler) {
		var $tempForm = $formTemplates.find('.add-edit-entry-form').clone().addClass('tempForm')
		
		$tempForm.children('.app-key').val(appKey)
		$tempForm.children('.entry-key').val(entryKey)
		$tempForm.children('.entry-value').val(entryValue)
		$tempForm.children('.entry-level').val(entryLevel)
		$tempForm.on('submit', function() {
			var $this = $(this)
			$this.find('input').removeClass('error-highlight')
			$.ajax({
				url 	: '/appvars',
				type	: 'POST',
				data	: $this.serialize(),
				success	: successHandler,
				error: function() {
					$this.find('input').addClass('error-highlight')
				}
			})
			
			return false
		});
		
		return $tempForm
	}
	
	function dictLevelControlsScripts($entryElement) {
		if (arguments.length == 0) {
			$dictControls = $('.dict-level-controls')
		}
		else {
			$dictControls = $entryElement.find('.dict-level-controls')
		}
		
		$dictControls.find('.minimize-dict-level').on('click', function() {
			$(this).parent().nextAll().slideToggle();
		});
		
		$dictControls.find('.add-entry').on('click', function() {
			var $dictControls = $(this).parent()
			var $dictEntries = $dictControls.closest('.dict-entries')
			
			if ($dictControls.children('form').length > 0) {
				return false
			}
			
			var newEntryKey = null
			var $addForm = addEditEntryForm(
								getAppKey($dictControls), 
								null, 
								null, 
								getDictLevel($dictControls),
								function(data, text, jqXHR) {
									$addForm.remove()
									var $data = $(data)
									
									dictLevelControlsScripts($data)
									entryLevelControlsScripts($data)
									$data.appendTo($dictEntries)
								}
							)
			
			$addForm.appendTo($dictControls)
			
			var parentEntryKey = getEntryKey($dictControls.closest('.dict-entry'))
			var $entryKey = $addForm.find('.entry-key')
			
			$('<input>')
				.attr({'type' : 'text'})
				.on('keyup change', function() {
					var currentVal = $(this).val()
					newEntryKey = currentVal
					$entryKey.val(parentEntryKey+'['+currentVal+']')
				})
				.insertAfter($entryKey)
		});
	}
	
	function entryLevelControlsScripts($entryElement) {
		if (arguments.length == 0) {
			$entryControls = $('.dict-entry-controls')
		}
		else {
			$entryControls = $entryElement.find('.dict-entry-controls')
			console.log($entryControls)
		}
		
		$entryControls.find('.edit-entry').on('click', function() {
			var $editControls = $(this)
			$editControls.hide()
			
			var $entry = $editControls.closest('.dict-entry')
			var $entryValue = $entry.children('.dict-value')
			var $source = $entryValue.children('.source')
			
			$entryValue.children('.value-entry').hide()
			
			var entryKey = getEntryKey($entry)
			
			$entryValue.append(
				addEditEntryForm(
					getAppKey($entry), 
					entryKey, 
					$source.val(), 
					getDictLevel($entry),
					function(data, text, jqXHR) {
						var $data = $(data)
						
						$entry.replaceWith($data)
						entryLevelControlsScripts($data)
					}
				)
			)
		});
		
		$entryControls.find('.delete-entry').on('click', function() {
			var $this = $(this)
			var $entry = $this.closest('.dict-entry')
			
			$entry.addClass('updated-highlight')
			
			if (confirm('Remove this entry?'))
			{
				var $deleteForm = $formTemplates.find('.delete-entry-form')
				
				$deleteForm.children('.app-key').val(getAppKey($this))
				$deleteForm.children('.entry-key').val(getEntryKey($this))
				
				$this.closest('.dict-entry').remove()
				$deleteForm.submit()
			}
			else
			{
				$entry.removeClass('updated-highlight')
			}
		});
	}
	
	dictLevelControlsScripts()
	entryLevelControlsScripts()
	
	$('.dict-level-0 > .dict-level-controls .minimize-dict-level').trigger('click')
	
	$('.edit-source').on('click', function() {
		$(this).closest('.app-variable').find('.source_form').toggle()
	});
	
	$('.source_form').on('submit', function() {
		var $this = $(this)
		$this.find('textarea').removeClass('error-highlight').removeClass('updated-highlight')
		$.ajax({
			url: '/appvars',
			type: 'POST',
			data: $this.serialize(),
			success: function(data, text, jqXHR) {
				$this.find('textarea').val(data).removeClass('error-highlight').addClass('updated-highlight')
			},
			error: function() {
				$this.find('textarea').removeClass('updated-highlight').addClass('error-highlight')
			}
		})
		
		return false
	});
	
	$formTemplates.find('.delete-entry-form').on('submit', function() {
		var $this = $(this)
		$this.children('.entry-value').val('1')
		$.ajax({
			url 	 : '/appvars',
			type	 : 'POST',
			data	 : $this.serialize(),
			complete : function() {
				$this.children('.app-key').val(null)
				$this.children('.entry-key').val(null)
			}
		})
		
		return false
	});
});