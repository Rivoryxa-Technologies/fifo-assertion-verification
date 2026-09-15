// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module fifo_properties #(parameter int ASIZE=2)(
 input logic wclk, wrst_n, winc, wfull,
 input logic rclk, rrst_n, rinc, rempty,
 input logic [ASIZE:0] wbin,wgray,rbin,rgray,wptr_rq1,wptr_rq2,rptr_wq1,rptr_wq2
);
 logic wpast=0,rpast=0;
 integer blocked_writes=0, blocked_reads=0, write_wraps=0, read_wraps=0;
 function automatic logic [ASIZE:0] gray_to_bin(input logic [ASIZE:0] gray);
   integer bit_index;
   begin
     gray_to_bin[ASIZE]=gray[ASIZE];
     for(bit_index=ASIZE-1;bit_index>=0;bit_index=bit_index-1)
       gray_to_bin[bit_index]=gray_to_bin[bit_index+1]^gray[bit_index];
   end
 endfunction
 function automatic logic expected_full(
   input logic [ASIZE:0] previous_wbin,
   input logic [ASIZE:0] synchronized_rgray,
   input logic accepted_write
 );
   logic [ASIZE:0] candidate_wbin,synchronized_rbin;
   begin
     candidate_wbin=previous_wbin+(ASIZE+1)'(accepted_write);
     synchronized_rbin=gray_to_bin(synchronized_rgray);
     expected_full=(candidate_wbin[ASIZE]!=synchronized_rbin[ASIZE]) &&
                   (candidate_wbin[ASIZE-1:0]==synchronized_rbin[ASIZE-1:0]);
   end
 endfunction
 function automatic logic expected_empty(
   input logic [ASIZE:0] previous_rbin,
   input logic [ASIZE:0] synchronized_wgray,
   input logic accepted_read
 );
   logic [ASIZE:0] candidate_rbin;
   begin
     candidate_rbin=previous_rbin+(ASIZE+1)'(accepted_read);
     expected_empty=(candidate_rbin==gray_to_bin(synchronized_wgray));
   end
 endfunction
 always @(posedge wclk or negedge wrst_n)
   if (!wrst_n) wpast <= 0; else begin
     wpast <= 1;
     if(winc && wfull) blocked_writes <= blocked_writes+1;
     if(wpast && wbin[ASIZE-1:0]==0 && $past(wbin[ASIZE-1:0])=='1) write_wraps <= write_wraps+1;
   end
 always @(posedge rclk or negedge rrst_n)
   if (!rrst_n) rpast <= 0; else begin
     rpast <= 1;
     if(rinc && rempty) blocked_reads <= blocked_reads+1;
     if(rpast && rbin[ASIZE-1:0]==0 && $past(rbin[ASIZE-1:0])=='1) read_wraps <= read_wraps+1;
   end
 assert property (@(posedge wclk) disable iff (!wrst_n || !wpast)
   $onehot0(wgray ^ $past(wgray))) else $fatal(1,"WRITE_GRAY_FAILED");
 assert property (@(posedge rclk) disable iff (!rrst_n || !rpast)
   $onehot0(rgray ^ $past(rgray))) else $fatal(1,"READ_GRAY_FAILED");
 assert property (@(posedge wclk) disable iff (!wrst_n || !wpast)
   wbin == ($past(wbin) + (ASIZE+1)'($past(winc && !wfull)))) else $fatal(1,"WRITE_POINTER_FAILED");
 assert property (@(posedge rclk) disable iff (!rrst_n || !rpast)
   rbin == ($past(rbin) + (ASIZE+1)'($past(rinc && !rempty)))) else $fatal(1,"READ_POINTER_FAILED");
 assert property (@(posedge rclk) disable iff (!rrst_n || !rpast)
   wptr_rq2 == $past(wptr_rq1)) else $fatal(1,"WRITE_SYNC_PIPELINE_FAILED");
 assert property (@(posedge wclk) disable iff (!wrst_n || !wpast)
   rptr_wq2 == $past(rptr_wq1)) else $fatal(1,"READ_SYNC_PIPELINE_FAILED");
 assert property (@(posedge wclk) disable iff (!wrst_n || !wpast)
   wfull == expected_full($past(wbin),$past(rptr_wq2),$past(winc && !wfull)))
   else $fatal(1,"FULL_FLAG_FAILED");
 assert property (@(posedge rclk) disable iff (!rrst_n || !rpast)
   rempty == expected_empty($past(rbin),$past(wptr_rq2),$past(rinc && !rempty)))
   else $fatal(1,"EMPTY_FLAG_FAILED");
 cover property (@(posedge wclk) wpast && winc && wfull);
 cover property (@(posedge rclk) rpast && rinc && rempty);
endmodule
bind async_fifo fifo_properties #(.ASIZE(ASIZE)) checks(.*);
