jQuery(document).ready(function ($) {

    var auction_entry_html = ` 
        <div class="auction-entry">
          <a href="#"><img src="img/test_img_auction_main.jpg" class="auction-entry-image" /></a>
          <div class="auction-entry-info">
              <h4><a href="#">Subaru Impreza Wagon</a></h4>
              <p>
                <span>ROK PRODUKCJI:</span> <b>2010</b><br/>
                <span>PRZEBIEG:</span> <b>220 000km</b><br/>
              </p>
          </div>
          <div class="auction-entry-buy-info">
              <p class="auction-end-info">
                <span>KONIEC AUKCJI:</span> <b>5.04.2017 GODZ. 20:00</b><br/>
                <span>DO KOŃCA AUKCJI: <b></b></br>
              </p>
              <p class="auction-bet-info">
	      <!--
                <span>TWOJA PROPOZYCJA:</span> <b>12 000 zł</b>
	      -->
              </p>
          </div>
          <div class="auction-entry-actions">
		  <span class="auctions-observations1">
			  <span class="auction-action-add-to-observed" data-auction-id="" style="display:block;cursor:pointer">
				DODAJ DO OBSERWOWANYCH
			  </span>
			  <span class="auction-action-remove-from-observed" data-auction-id="" style="display:none;cursor:pointer">
				PRZESTAŃ OBSERWOWAĆ
			  </span>
		  </span>
            <span class="auction-action-make-offer">
                 <a href="#">więcej</a>
                 <span>
                 </span>
            </span>
          </div>
          <div class="auction-entry-clock-icon">
          </div>
        </div>
        <div style="clear:both"></div>
        `
    var auctions_container = $('.auctions-container .content .content-inner');

    function load_data(page=1){
        $.get('/api/v1/auctions/?format=json&page='+page.toString()).done(function(data){
            $.each(data, function(i, item){
                auctions_container.append(auction_entry_html);
                var entry = $('.auction-entry').last();

		entry.find('.auction-action-remove-from-observed').attr('data-auction-id', item['id']);
		entry.find('.auction-action-add-to-observed').attr('data-auction-id', item['id']);

                entry.find('.auction-entry-info h4 a').text(item['title'].substring(0, 55));
                entry.find('img').attr('src', '/' + item['photos']);
		if (item['observerd'] == true)
		{
			entry.find('.auction-action-remove-from-observed').show();
			entry.find('.auction-action-add-to-observed').hide();
		}
		var logged = $('.dropdown-toggle').length > 0;

		if (!logged) {
			var button_info = entry.find('.auction-action-add-to-observed');
			button_info.attr('data-toggle', 'tooltip'); 
			button_info.attr('data-placement', 'top'); 
			button_info.attr('title', 'Aby dodać aukcję do obserwowanych zarejestruj się!'); 
			button_info.tooltip();
		}
                entry.find('.auction-entry-info b:eq(0)').text(item['production_date']);
                entry.find('.auction-entry-info b:eq(1)').text(item['run'] + ' km');

            	var end_date_ms = Date.parse(item['end_date']);
            	var end_date = new Date(end_date_ms);
	    	var minutes = (end_date.getMinutes()<10?'0':'') + end_date.getMinutes();
	    	var hours = (end_date.getHours()<10?'0':'') + end_date.getHours();
	    	var seconds = (end_date.getSeconds()<10?'0':'') + end_date.getSeconds();
            	var end_date_str = end_date.getDate() + '-' + (end_date.getMonth() + 1) + '-' + end_date.getFullYear() + ' ' + hours + ':' + minutes + ':' + seconds;
            	entry.find('.auction-end-info b:eq(0)').text(end_date_str);

            	entry.find('a').attr('href', '/aukcje/licytacja/' + item['id'] + '/' + item['title'].toLowerCase().replace(/\W/g, '-'));

		    var parsed_date = end_date;

		    var seconds = parsed_date.getTime() / 1000;
		    entry.attr('data-end', seconds);

		    var currentTime = new Date();
		    var diff = seconds - currentTime.getTime()/1000;

		    var daysDiff = parseInt(diff / (24*3600));
		    var rest = diff % (24*3600);
		    var hoursDiff = parseInt(rest / 3600);
		    var rest = rest % 3600;
		    var minutesDiff = parseInt(rest / 60);
		    var secondsDiff = parseInt(rest % 60);

                    var text = '';
		    if (daysDiff > 0)
		        text = daysDiff + 'dni ' + hoursDiff + 'godz ' + minutesDiff + 'min';
		    else
		        text = hoursDiff + 'godz ' + minutesDiff + 'min ' + secondsDiff + 's ';

		    entry.find('b').eq(3).text(text);
            });
        });
    }

    $(document).on('click', '.auctions-paginator li', function(e){
        e.preventDefault();
        if ($(this).hasClass('disabled'))
            return;

        var page = $(this).text().toString();
        var url = window.location.href;
        var url_splitted = url.split("aukcje/");
        var current_page = 1;

        if (url_splitted.length == 2 && url_splitted[1] != "")
            current_page = parseInt(url_splitted[1]);

        if ($(this).hasClass('prev_paginator'))
            page = current_page - 1;
        else if($(this).hasClass('next_paginator'))
            page = current_page + 1;

        var thisClicked = $(this);

        auctions_container.fadeOut(200, function(){
           $(this).html('');
           load_data(page);
           load_paginator(page);
           $(this).delay(200).fadeIn(400);
           
           document.title = document.title.split(" - strona")[0] + ' - strona ' + page.toString();
           var urlPath = "/aukcje/"+page.toString()+"/";
           window.history.pushState({"pageTitle": document.title}, "", urlPath);
           $('html,body').scrollTop(0);
        });
    });

    function load_paginator(page){
        var paginator = $('.auctions-paginator');
        paginator.html('');
        page = parseInt(page);
        var max_page = parseInt($('.auctions-container').attr('data-max-page'));
        var paging_to_left = Math.max(1, page-3);
        var paging_to_right = Math.min(max_page, page+3);

        if (page > 1)
          paginator.append('<li class="prev_paginator"><a href="/aukcje/'+(page-1)+'" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a></li>');
        else
          paginator.append('<li class="prev_paginator disabled"><a href="/aukcje/'+(page-1)+'" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a></li>');

        if (paging_to_left > 2)
          paginator.append('<li class="first_paginator"><a href="/aukcje/1" aria-label="First"><span aria-hidden="true">1</span></a></li><li class="more_paginator disabled"><a href="#" aria-label="More"><span aria-hidden="true">...</span></a></li>');
        else if (paging_to_left > 1)
           paginator.append('<li class="first_paginator"><a href="/aukcje/1" aria-label="First"><span aria-hidden="true">1</span></a></li>');

        for (var page_count=0;page_count<4;page_count++)
        {
           if (page_count + paging_to_left < page)
             paginator.append('<li><a href="/aukcje/'+(page_count+paging_to_left)+'">'+(page_count+paging_to_left)+'</a></li>');
        } 
        paginator.append('<li class="active"><a href="/aukcje/'+page+'">' + page + '</a></li>');
        for (var page_count=1;page_count<5;page_count++)
        {
           if (page_count + page <= paging_to_right)
               paginator.append('<li><a href="/aukcje/'+(page_count+page)+'">' + (page_count + page) +'</a></li>');
        }       
        if (paging_to_right < max_page - 1)
        {
                paginator.append('<li class="more_paginator disabled"><a href="#" aria-label="More"><span aria-hidden="true">...</span></a></li>');
                 paginator.append('<li class="last_paginator"><a href="/aukcje/'+max_page+'" aria-label="Last"><span aria-hidden="true">'+max_page+'</span></a></li>');
        }
        else if (paging_to_right < max_page)
                  paginator.append('<li class="last_paginator"><a href="/aukcje/'+max_page+'" aria-label="Last"><span aria-hidden="true">'+max_page+'</span></a></li>');
        
        if (page < max_page)
            paginator.append('<li class="next_paginator"><a href="/aukcje/'+(page+1)+'" aria-label="Next"><span aria-hidden="true">&raquo;</span></a></li>');
        else
            paginator.append('<li class="next_paginator disabled"><a href="/aukcje/'+(page+1)+'" aria-label="Next"><span aria-hidden="true">&raquo;</span></a></li>');
    }

    $(function () {
          $('[data-toggle="tooltip"]').tooltip()
    });

    $(document).on('click', '.auction-action-add-to-observed', function(e){
	var url = '/api/v1/obserwuj/';
	var data = {
		'auction_id': $(this).attr('data-auction-id'),
		'csrfmiddlewaretoken': $('.auctions-container').attr('data-token'),
	};

	var parent_item = $(this).closest('.auction-entry-actions');
	var this_item = $(this);

	$.post(url, data).done(function(data){
		this_item.fadeOut(200, function(){
			parent_item.find('.auction-action-remove-from-observed').fadeIn(300);
		});
	}).fail(function(){
		this_item;
	});
    });

    $(document).on('click', '.auction-action-remove-from-observed', function(e){
	var url = '/api/v1/nieobserwuj/';
	var data = {
		'auction_id': $(this).attr('data-auction-id'),
		'csrfmiddlewaretoken': $('.auctions-container').attr('data-token'),
	};

	var parent_item = $(this).closest('.auction-entry-actions');
	var this_item = $(this);

	$.post(url, data).done(function(data){
		this_item.fadeOut(200, function(){
			parent_item.find('.auction-action-add-to-observed').fadeIn(300);
		});
	});
    });

    var currentTime = moment().tz("Europe/Warsaw")._d;
    $('.auction-entry').each(function(index, element){
	    var date = $(this).find('.auction-end-info').find('b').eq(0).text();
	    new_date = date.substring(0, 2);
	    new_date = date.substring(3, 5) + '-' + new_date;
	    new_date = date.substring(6, 10) + '-' + new_date;
	    new_date += 'T';
	    new_date += date.substr(11);

	    var MOBILE_SAFARI = ((navigator.userAgent.toString().toLowerCase().indexOf("iphone")!=-1) || (navigator.userAgent.toString().toLowerCase().indexOf("ipod")!=-1) || (navigator.userAgent.toString().toLowerCase().indexOf("ipad")!=-1)) ? true : false;
            var SAFARI = (navigator.userAgent.toString().toLowerCase().indexOf("safari") != -1) && (navigator.userAgent.toString().toLowerCase().indexOf("chrome") == -1);

	    new_date += 'Z';

	    var parsed_date = new Date(new_date);
	    var seconds = parsed_date.getTime() / 1000;
	    $(this).attr('data-end', seconds);

	    var diff = seconds - currentTime.getTime()/1000;

	    if (diff <= 0){
		    $(this).find('.auction-end-info').find('b').eq(1).html('<span style="color:#ac0303";>ZAKO&#323;CZONO</span>');
		    return;
	    }

	    var daysDiff = parseInt(diff / (24*3600));
	    var rest = diff % (24*3600);
	    var hoursDiff = parseInt(rest / 3600);
	    var rest = rest % 3600;
	    var minutesDiff = parseInt(rest / 60);
	    var secondsDiff = parseInt(rest % 60);

	    var text = '';
	    if (daysDiff > 0)
		text = daysDiff + 'dni ' + hoursDiff + 'godz ' + minutesDiff + 'min';
	    else
		text = hoursDiff + 'godz ' + minutesDiff + 'min ' + secondsDiff + 's ';

	    $(this).find('.auction-end-info').find('b').eq(1).text(text);
    });

	function customInterval(duration, fn){
	  this.baseline = undefined
	  
	  this.run = function(){
	    if(this.baseline === undefined){
	      this.baseline = new Date().getTime()
	    }
	    fn()
	    var end = new Date().getTime()
	    this.baseline += duration
	 
	    var nextTick = duration - (end - this.baseline)
	    if(nextTick<0){
	      nextTick = 0
	    }
	    (function(i){
		i.timer = setTimeout(function(){
		i.run(end)
	      }, nextTick)
	    }(this))
	  }

	this.stop = function(){
	   clearTimeout(this.timer)
	 }
	}


        var customTimer = new customInterval(1000, function(){
            currentTime = moment().tz("Europe/Warsaw")._d;
	    $('.auction-entry').each(function(index, element){
		    var seconds = $(this).attr('data-end');

		    var diff = seconds - currentTime.getTime()/1000;

		    var MOBILE_SAFARI = ((navigator.userAgent.toString().toLowerCase().indexOf("iphone")!=-1) || (navigator.userAgent.toString().toLowerCase().indexOf("ipod")!=-1) || (navigator.userAgent.toString().toLowerCase().indexOf("ipad")!=-1)) ? true : false;
		    var SAFARI = (navigator.userAgent.toString().toLowerCase().indexOf("safari") != -1) && (navigator.userAgent.toString().toLowerCase().indexOf("chrome") == -1);

                    if (diff <= 0){
			    $(this).find('.auction-end-info').find('b').eq(1).html('<span style="color:#ac0303";>ZAKO&#323;CZONO</span>');
                            return;
		    }

		    var daysDiff = parseInt(diff / (24*3600));
		    var rest = diff % (24*3600);
		    var hoursDiff = parseInt(rest / 3600);
		    var rest = rest % 3600;
		    var minutesDiff = parseInt(rest / 60);
		    var secondsDiff = parseInt(rest % 60);

		    var text = '';
		    if (daysDiff > 0)
			text = daysDiff + 'dni ' + hoursDiff + 'godz ' + minutesDiff + 'min';
		    else
			text = hoursDiff + 'godz ' + minutesDiff + 'min ' + secondsDiff + 's ';

		    $(this).find('.auction-end-info').find('b').eq(1).text(text);
	    });
        });

        customTimer.run();
});

