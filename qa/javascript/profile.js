function setHideAndShowEvents(){
    $('#button-show-add-topics-form').click(
        {a: 'div-add-topics-form', b: 'div-show-add-topics', c: 'div-hide-add-topics'},
        showAddForm
    );

    $('#button-hide-add-topics-form').click(
        {a: 'div-add-topics-form', b: 'div-show-add-topics', c: 'div-hide-add-topics'},
        hideAddForm
    );

    $('#button-show-add-question-set-form').click(
        {a: 'div-add-question-set-form', b: 'div-show-add-question-set', c: 'div-hide-add-question-set'},
        showAddForm
    );

    $('#button-hide-add-question-set-form').click(
        {a: 'div-add-question-set-form', b: 'div-show-add-question-set', c: 'div-hide-add-question-set'},
        hideAddForm
    );
}

function collapsibleListHandler(){
    $('.list-group-item').on('click', function() {
        $('.glyphicon', this)
          .toggleClass('glyphicon-chevron-right')
          .toggleClass('glyphicon-chevron-down');
    });
}
function handleTopicDelete(e){
    //Delete the topic choice from the question set creation form's select box.
    var list = $('.topic-choices')[0].getElementsByTagName('option');
    for (var i = 0; i < list.length; i++) {
        if (list[i].textContent == e.detail.resource_name) {
            $(list[i]).remove();
            if (list.length == 1) //No more topics, remove question set related stuff.
                $('#new-question-sets').remove();
            break;
        }
    }
    //Check if there are any topics left, and if so, delete the list group div.
    //The resource-container class is used for question-sets too, but if there are no
    //topics, then there are no question sets.
    if (!$('.resource-container').length)
        $('#resource-master-container').remove();
}

$(document).ready(function(){
    $('#div-hide-add-topics').hide();
    $('#div-add-topics-form').hide();
    $('#div-hide-add-question-set').hide();
    $('#div-add-question-set-form').hide();
    setHideAndShowEvents();
    collapsibleListHandler();

    $(window).on('deleteResource', function(e){
        if(e.detail.resource_type == 'topic')
            handleTopicDelete(e);
    })
});
