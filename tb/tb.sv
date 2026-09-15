// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb;
 logic wclk=0,rclk=0,wrst_n=0,rrst_n=0,winc=0,rinc=0;
 logic [7:0] wdata=0,rdata;
 logic wfull,rempty;
 integer whalf=5,rhalf=7,received=0;
 async_fifo #(.DSIZE(8),.ASIZE(2)) dut(.*);
 initial begin
   if (!$value$plusargs("WHALF=%d",whalf)) whalf=5;
   forever #(whalf) wclk=~wclk;
 end
 initial begin
   if (!$value$plusargs("RHALF=%d",rhalf)) rhalf=7;
   forever #(rhalf) rclk=~rclk;
 end
 initial begin
   #100000; $fatal(1,"WATCHDOG_FAILED");
 end
 initial begin
   #1; wrst_n=1; rrst_n=1; #1; wrst_n=0; rrst_n=0;
   repeat(4) @(negedge wclk); wrst_n=1;
   repeat(4) @(negedge rclk); rrst_n=1;
   for(integer round=0;round<4;round=round+1) begin
     // Fill, then keep requesting writes while full. The local pointer must hold.
     for(integer i=0;i<4;i=i+1) begin
       @(negedge wclk); while(wfull) @(negedge wclk);
       winc=1; wdata=8'(round*4+i);
     end
     @(negedge wclk); repeat(4) @(negedge wclk); winc=0;
     // Drain after the write pointer has crossed the synchronizer.
     for(integer i=0;i<4;i=i+1) begin
       @(negedge rclk); while(rempty) @(negedge rclk);
       rinc=1;
       @(posedge rclk);
       if(rdata !== 8'(round*4+i)) $fatal(1,"DATA_ORDER_FAILED");
       received=received+1;
       @(negedge rclk); rinc=0;
     end
     @(negedge rclk); rinc=1;
     repeat(4) @(negedge rclk); rinc=0;
   end
   repeat(4) @(negedge wclk);
   repeat(4) @(negedge rclk);
   if(received!=16 || dut.checks.blocked_writes==0 || dut.checks.blocked_reads==0 ||
      dut.checks.write_wraps<4 || dut.checks.read_wraps<4) $fatal(1,"EXERCISE_COUNTS_FAILED");
   $display("EXERCISE received=%0d blocked_writes=%0d blocked_reads=%0d write_wraps=%0d read_wraps=%0d",received,dut.checks.blocked_writes,dut.checks.blocked_reads,dut.checks.write_wraps,dut.checks.read_wraps);
   $display("FIFO_ASSERTIONS_PASS"); $finish;
 end
endmodule
